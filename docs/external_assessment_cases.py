from ..schemas import ImagePromptFullSchema, ImagePromptWithIdSchema, ImagePromptWithImagesSchema, StudentDataForQuestionListSchema

from ..services import ImagePromptService
from ..storages import ExternalImageStorage, ImagePromptStorage


class ExternalAssessmentCases:
    def __init__(
        self,
        image_prompt_service: ImagePromptService,
        external_image_storage: ExternalImageStorage,
        image_prompt_storage: ImagePromptStorage,
    ):
        self.image_prompt_service = image_prompt_service
        self.external_image_storage = external_image_storage
        self.image_prompt_storage = image_prompt_storage

    # TODO: check if request schema changed
    async def create_prompts(self, image_prompts: list[ImagePromptWithImagesSchema]):
        image_prompts_with_images = await self._create_image_prompts(image_prompts)
        await self._create_external_images(image_prompts_with_images)
        await self.image_prompt_service.process_images_prompts(image_prompts_with_images)

    async def create_question_list_prompt(self, question_list_images: StudentDataForQuestionListSchema) -> None:
        """
        Creates a question list prompt using the provided image question list schema.

        This method processes a list of image-based questions
        using the image prompt service.

        Args:
            question_list_images (StudentDataForQuestionListSchema): The schema containing
                the list of aws_path of images and assessment_id.

        Returns:
            None
        """
        await self.image_prompt_service.process_question_list_prompt(question_list_images)

    async def delete_prompts(self, external_assessment_ids: list[int]):
        await self.image_prompt_storage.bulk_delete(external_assessment_ids)

    async def _create_image_prompts(
        self,
        image_prompts: list[ImagePromptWithImagesSchema],
    ) -> list[ImagePromptFullSchema]:
        extra_fields = {'pages_per_student', 'prompt', 'images', 'model_assessment', 'question_list'}

        image_prompts_to_create = [image.model_dump(exclude=extra_fields) for image in image_prompts]
        image_prompts_with_id = await self.image_prompt_storage.bulk_create(image_prompts_to_create)

        return self._prepare_image_prompts_with_images(
            image_prompts_with_id,
            image_prompts,
            extra_fields,
        )

    async def _create_external_images(self, image_prompts: list[ImagePromptFullSchema]):
        external_images_to_create = self._prepare_external_images_to_create(image_prompts)
        await self.external_image_storage.bulk_create(external_images_to_create)

    @staticmethod
    def _prepare_image_prompts_with_images(
        image_prompts_with_id: list[ImagePromptWithIdSchema],
        image_prompts_with_images: list[ImagePromptWithImagesSchema],
        extra_fields: set,
    ) -> list[ImagePromptFullSchema]:
        full_image_prompts = []

        for image_prompt_with_id, image_prompt_with_image in zip(image_prompts_with_id, image_prompts_with_images):
            full_image_prompts.append(
                ImagePromptFullSchema(
                    **image_prompt_with_id.model_dump(),
                    **image_prompt_with_image.model_dump(include=extra_fields),
                )
            )

        return full_image_prompts

    @staticmethod
    def _prepare_external_images_to_create(
        image_prompts: list[ImagePromptFullSchema],
    ) -> list[dict]:
        external_images_to_create = []

        for image_prompt in image_prompts:
            for image in image_prompt.images:
                external_images_to_create.append(
                    {
                        'image_prompt_process_id': image_prompt.id,
                        'external_image_id': image.id,
                        'page_number': image.page_number,
                    }
                )

        return external_images_to_create
