from pydantic import parse_obj_as, ValidationError

from core.loggers import logger

from ..exceptions import ExternalAssessmentGradingException
from ..schemas import ImagePromptBatchSchema
from ..schemas.external_assessment_result_schema import ExternalAssessmentStudentResultSchema, ExternalAssessmentResultSchema

from ..storages import ImagePromptBatchStorage, ImagePromptStorage
from ..types import ExternalResultProcessingStatuses, ImagePromptBatchProcessStatus, ImagePromptStatus


class ExternalAssessmentGradingResultsService:
    def __init__(
        self,
        api_service,
        image_prompt_batch_storage: ImagePromptBatchStorage,
        image_prompt_storage: ImagePromptStorage,
    ):
        self.api_service = api_service
        self.image_prompt_batch_storage = image_prompt_batch_storage
        self.image_prompt_storage = image_prompt_storage

    async def call(self, image_prompt_process_id: int):
        try:
            batch_results = await self._get_successful_batch_results(image_prompt_process_id)
            parsed_data = self._format_batch_results(batch_results)
            await self._complete_recognition_results(image_prompt_process_id)
            await self._send_results_to_api(
                image_prompt_process_id,
                status=ExternalResultProcessingStatuses.SUCCESS,
                data=parsed_data,
            )
        except ExternalAssessmentGradingException as external_assessment_grading_exception:
            logger.error(external_assessment_grading_exception)
            logger.error(f'image_prompt_process_id: {image_prompt_process_id}')
            await self._fail_recognition_results(image_prompt_process_id)
            await self._send_results_to_api(
                image_prompt_process_id,
                status=ExternalResultProcessingStatuses.FAILED,
                data=None,
            )

    async def _get_successful_batch_results(self, image_prompt_process_id: int) -> list[ImagePromptBatchSchema]:
        batch_results = await self.image_prompt_batch_storage.list_objects(
            image_prompt_process_id=image_prompt_process_id,
            status=ImagePromptBatchProcessStatus.COMPLETED,
            order_by="id"
        )
        if not batch_results:
            raise ExternalAssessmentGradingException('No successfully finished batches.')

        return batch_results

    async def _complete_recognition_results(self, image_prompt_process_id: int):
        await self.image_prompt_storage.update(
            id=image_prompt_process_id,
            status=ImagePromptStatus.COMPLETED,
        )

    async def _fail_recognition_results(self, image_prompt_process_id: int):
        await self.image_prompt_storage.update(
            id=image_prompt_process_id,
            status=ImagePromptStatus.FAILED,
        )

    def _format_batch_results(
        self,
        batch_results: list[ImagePromptBatchSchema],
    ) -> list[ExternalAssessmentStudentResultSchema]:
        result = []

        for batch in batch_results:
            try:
                parsed_response = self.__parse_gpt_response_data(batch)
            except Exception as exc:  # TODO: replace with more precise exceptions
                logger.error(f'Could not parse GPT response. Error: {exc}')
                continue

            result.extend(parsed_response)

        if not result:
            raise ExternalAssessmentGradingException('Could not successfully parse at least one batch result')

        return result

    @staticmethod
    def __parse_gpt_response_data(
        batch: ImagePromptBatchSchema,
    ) -> list[ExternalAssessmentStudentResultSchema]:
        try:
            return parse_obj_as(list[ExternalAssessmentStudentResultSchema], batch.response_log.get('result'))
        except ValidationError as validation_error:
            raise ExternalAssessmentGradingException(
                'Could not format GPT response data to internal format.'
                f' Error: {validation_error}. GPT response data: {batch.response_log}.'
            )

    async def _send_results_to_api(
        self,
        image_prompt_process_id: int,
        status: ExternalResultProcessingStatuses,
        data: list[ExternalAssessmentStudentResultSchema] | None,
    ):
        external_assessment_results_data = await self.__prepare_external_assessment_results_data(
            image_prompt_process_id,
            status,
            data,
        )
        await self.api_service.save_external_assessment_results(external_assessment_results_data.dict())

    async def __prepare_external_assessment_results_data(
        self,
        image_prompt_process_id: int,
        status: ExternalResultProcessingStatuses,
        data: list[ExternalAssessmentStudentResultSchema] | None,
    ) -> ExternalAssessmentResultSchema:
        image_prompt = await self.image_prompt_storage.get_object(id=image_prompt_process_id)

        return ExternalAssessmentResultSchema(
            assessment_id=image_prompt.external_assessment_id,
            assessment_settings_id=image_prompt.external_assessment_settings_id,
            status=status,
            data=data or [],
        )
