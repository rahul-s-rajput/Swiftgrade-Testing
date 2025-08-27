import json
from collections import defaultdict
from math import floor
from typing import Optional, List, Dict, Union

from loguru import logger

from celery import chain, chord, group

import settings as env

from .image_token_service import ImageTokenService
from ..constants import SYSTEM_MESSAGE_FOR_QUESTION_LIST, \
    SYSTEM_MESSAGE_EXTERNAL_ASSESSMENT, MODEL_ASSESSMENT_MESSAGE
from ..schemas import ImagePromptBatchSchema, ImagePromptFullSchema, ImageSchema, GPTGradingResultResponseSchema
from ..schemas.question_list_prompt_schema import StudentDataForQuestionListSchema, QuestionItemSchema, \
    QuestionListResponseSchema
from ..storages import ImagePromptStorage, ImagePromptBatchStorage
from ..tasks import preprocess_batch, process_batch, process_batches_results, preprocess_question_list, \
    process_question_list, process_question_list_result
from ..types import ImagePromptStatus, ImagePromptBatchProcessStatus


class ImagePromptService:
    def __init__(
        self,
        image_token_service: ImageTokenService,
        image_prompt_storage: ImagePromptStorage,
        image_prompt_batch_storage: ImagePromptBatchStorage,
    ):
        self.image_token_service = image_token_service
        self.image_prompt_storage = image_prompt_storage
        self.image_prompt_batch_storage = image_prompt_batch_storage

    def _calculate_batch_size(self, raw_prompt_tokens: int) -> int:
        """Calculates batch size with RTG limitations applied."""
        batch_size = self.image_token_service.calculate_batch_size(raw_prompt_tokens)

        # TODO: use RTG_MAX_BATCH_SIZE as a temporary limit for images amount per request to GPT,
        # because gpt-4o returns incomplete results if batch size is too big.
        # https://community.openai.com/t/latest-model-gpt-4o-2024-08-06-reduced-number-of-token-for-result/898760
        # https://community.openai.com/t/o4-mini-high-and-o3-context-window-issue-and-high-hallucination-rate/1236872
        if (
            batch_size * env.OUTPUT_TOKENS_PER_IMAGE > env.RTG_MAX_COMPLETION_TOKENS or
            batch_size > env.RTG_MAX_BATCH_SIZE
        ):
            batch_size = min(floor(env.RTG_MAX_COMPLETION_TOKENS / env.OUTPUT_TOKENS_PER_IMAGE), env.RTG_MAX_BATCH_SIZE)
        
        return batch_size

    async def process_images_prompts(self, image_prompts: list[ImagePromptFullSchema]):
        batch_tasks = defaultdict(list)

        for image_prompt in image_prompts:
            image_prompt_process_id = image_prompt.id
            pages_per_student = image_prompt.pages_per_student
            prompt = image_prompt.prompt if image_prompt.prompt else ''
            question_list = image_prompt.question_list
            model_assessment = image_prompt.model_assessment

            system_message = self._format_system_message(question_list)

            raw_prompt_tokens = (
                self.image_token_service.calculate_raw_prompt_tokens(system_message, prompt) +
                self.image_token_service.tokens_per_response_schema(GPTGradingResultResponseSchema)
            )

            if model_assessment:
                raw_prompt_tokens += (
                    self.image_token_service.tokens_per_system_message(MODEL_ASSESSMENT_MESSAGE) +
                    self.image_token_service.tokens_per_image * len(model_assessment)
                )

            batch_size = self._calculate_batch_size(raw_prompt_tokens)

            if pages_per_student > batch_size:
                await self.image_prompt_storage.update(
                    id=image_prompt_process_id,
                    status=ImagePromptStatus.FAILED,
                )
                continue

            image_prompt_batches = await self._create_image_prompt_batches(
                image_prompt_process_id,
                prompt,
                batch_size,
                image_prompt.images,
                pages_per_student,
                system_message,
                model_assessment,
            )

            batch_tasks[image_prompt_process_id].extend([
                chain(
                    preprocess_batch.si(
                        image_prompt_process_id,
                        image_prompt_batch.id,
                        raw_prompt_tokens + self.image_token_service.tokens_per_image * len(
                            image_prompt_batch.image_ids),
                    ),
                    process_batch.si(image_prompt_batch.id, image_prompt_batch.request_log),
                )
                for image_prompt_batch in image_prompt_batches
            ])

        for image_prompt_process_id, tasks in batch_tasks.items():
            chord(group(tasks), process_batches_results.si(image_prompt_process_id)).delay()

    async def process_question_list_prompt(
            self,
            images_question_list_prompt: StudentDataForQuestionListSchema
    ) -> None:
        """Processes a question list prompt containing images(aws_paths).

        This method calculates the required token count for processing the prompt,
        determines the batch size, and ensures that the number of images does not exceed
        the allowed batch size before triggering the preprocessing task.
        """
        raw_prompt_tokens = (
            self.image_token_service.tokens_per_system_message(SYSTEM_MESSAGE_FOR_QUESTION_LIST) +
            self.image_token_service.tokens_per_response_schema(QuestionListResponseSchema)
        )
        batch_size = self._calculate_batch_size(raw_prompt_tokens)

        if len(images_question_list_prompt.images) > batch_size:
            logger.error(f'Could not form a batch for assessment_id: {images_question_list_prompt.assessment_id}')
            return

        ql_prompt = self._prepare_messages(SYSTEM_MESSAGE_FOR_QUESTION_LIST, images_question_list_prompt.images)
        chain(
            preprocess_question_list.si(
                images_question_list_prompt.assessment_id,
                raw_prompt_tokens +
                self.image_token_service.tokens_per_image *
                len(images_question_list_prompt.images),
            ),
            process_question_list.si(images_question_list_prompt.assessment_id, ql_prompt),
            process_question_list_result.s(images_question_list_prompt.assessment_id)
        ).delay()

    async def _create_image_prompt_batches(
        self,
        image_prompt_process_id: int,
        prompt: str,
        batch_size: int,
        images: list[ImageSchema],
        pages_per_student: int,
        system_message: str,
        model_assessment: list[str],
    ) -> list[ImagePromptBatchSchema]:

        images_batches = self._split_images_into_batches(batch_size, images, pages_per_student)
        image_prompt_batches_to_create = []

        for images_batch in images_batches:
            messages = self._prepare_messages(system_message, images_batch, prompt, model_assessment)

            image_prompt_batches_to_create.append(
                {
                    'image_prompt_process_id': image_prompt_process_id,
                    'image_ids': self._get_external_images_ids(images_batch),
                    'request_log': messages,
                }
            )

        return await self.image_prompt_batch_storage.bulk_create(image_prompt_batches_to_create)

    @staticmethod
    def _split_images_into_batches(
        batch_size: int,
        images: list[ImageSchema],
        pages_per_student: int,
    ) -> list[list[ImageSchema]]:
        """
        Based on pages_per_student and batch_size splits given lists of images into batches.
        Examples (for simplicity, let's leave only the list of image_ids):
        1.
            images: [1, 2, 1, 2, 1, 2]
            pages_per_student: 2
            batch_size: 3
            Output: [[1, 2], [1, 2], [1, 2]]
        2.
            images: [1, 1, 1, 1, 1]
            pages_per_student: 1
            batch_size: 3
            Output: [[1, 1, 1], [1, 1]]
        3.
            images: [1, 2, 3, 4, 1, 2, 3, 4]
            pages_per_student = 4
            batch_size = 4
            Output: [[1, 2, 3, 4], [1, 2, 3, 4]]
        4.
            images = [1, 1]
            pages_per_student = 1
            batch_size = 3
            Output: [[1, 1]]
        """
        batches = []
        current_batch = []
        i = 0

        while i < len(images):
            if len(current_batch) + pages_per_student <= batch_size:
                current_batch.extend(images[i:i + pages_per_student])
                i += pages_per_student
            else:
                batches.append(current_batch)
                current_batch = []

        batches.append(current_batch)

        return batches

    def _prepare_messages(
            self,
            system_message: str,
            images: list[Union[ImageSchema, str]],
            prompt: Optional[str] = None,
            model_assessment: Optional[list[str]] = None,
    ) -> List[Dict[str, str]]:
        formatted_images = self._format_images(images)

        message = [
            {
                'role': 'system',
                'content': system_message,
            },
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt or ''},
                    *formatted_images
                ]
            }
        ]

        if model_assessment:
            message[1]['content'].extend([
                {'type': 'text', 'text': MODEL_ASSESSMENT_MESSAGE},
                *self._format_images(model_assessment)
            ]
            )

        return message

    @staticmethod
    def _get_external_images_ids(images: list[ImageSchema]) -> list[int]:
        return [image.id for image in images]

    @staticmethod
    def _format_images(images: list[ImageSchema | str]) -> list[dict[str, str | dict[str, str | int]]]:
        """
            Formats a list of images for inclusion in a prompt.

            This method is used for processing images in both assessment evaluation
            and question list generation tasks. It supports two input formats:

            - `list[ImageSchema]`: objects containing `aws_path`
            - `list[str]`: strings containing direct AWS image paths

            Args:
                images (list[ImageSchema | str]): A list of images, either as `ImageSchema`
                                                  objects or as strings with image paths.

            Returns:
                list[dict[str, str | dict[str, str | int]]]: A list of formatted image data
                                                             ready to be used in a prompt.
            """
        return [{
            'type': 'image_url',
            'image_url': {
                'url': image.aws_path if isinstance(image, ImageSchema) else image,
                'detail': env.RTG_IMAGES_QUALITY,
            },
        } for image in images]

    @staticmethod
    def _format_system_message(question_list: list[QuestionItemSchema], system_message: str = SYSTEM_MESSAGE_EXTERNAL_ASSESSMENT):
        return system_message.format(
            question_list=json.dumps([question.model_dump() for question in question_list])
        )

    async def update_completed_prompt(self, image_prompt_batch_process_id: int, response: dict | list) -> None:
        await self.image_prompt_batch_storage.update(
            id=image_prompt_batch_process_id,
            status=ImagePromptBatchProcessStatus.COMPLETED,
            response_log=response,
        )

    async def update_failed_prompt(self, image_prompt_batch_process_id: int, response: dict | list) -> None:
        await self.image_prompt_batch_storage.update(
            id=image_prompt_batch_process_id,
            status=ImagePromptBatchProcessStatus.FAILED,
            response_log=response,
        )
