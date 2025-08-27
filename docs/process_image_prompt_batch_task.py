
from dependency_injector.wiring import inject, Provide
from loguru import logger

from celery_app import app
from core.exceptions import ChatGptVisionException
from core.shared.async_utils import run_coroutine
from settings import RTG_AI_MODEL, RTG_MAX_COMPLETION_TOKENS, RTG_RATE_LIMIT_BUCKET_KEY, RTG_AI_REASONING, \
    RTG_AI_VERBOSITY

from ..exceptions import GPTRateLimitException, RTGResourceLockException
from ..schemas.gpt_response_schema import GPTGradingResultResponseSchema
from ..services.rate_limiter import check_if_can_run_task


@app.task(bind=True, max_retries=None)
@inject
def preprocess_batch(
    self,
    image_prompt_id: int,
    image_prompt_batch_process_id: int,
    batch_tokens_count: int,
):
    try:
        can_run = check_if_can_run_task(image_prompt_id, image_prompt_batch_process_id, batch_tokens_count)
    except (GPTRateLimitException, RTGResourceLockException) as rate_limit_error:
        # TODO: revoking task means all other tasks means results should be deleted,
        #  otherwise more results can be returned to API after ready_to_retry
        logger.error(f'{rate_limit_error}\nimage_prompt_batch_process_id: {image_prompt_batch_process_id}')
        app.control.revoke(self.request.id)
        return

    if not can_run:
        raise self.retry(countdown=60)


@app.task(bind=True, max_retries=3, retry_jitter=True)
def process_batch(
    self,
    image_prompt_batch_process_id: int,
    messages: list[dict[str, str | dict[str, str | int]]]
):
    run_coroutine(process_gpt_response(self, image_prompt_batch_process_id, messages))


@inject
async def process_gpt_response(
    self,
    image_prompt_batch_process_id: int,
    messages,
    chat_gpt=Provide['chat_gpt'],
    image_prompt_service=Provide['image_prompt_service']
):
    try:
        # TODO: Create and pass a response schema for the ChatGPT response(response_format)
        response = await chat_gpt.ask_chatgpt(
            RTG_AI_MODEL,
            messages,
            RTG_MAX_COMPLETION_TOKENS,
            RTG_AI_REASONING,
            RTG_AI_VERBOSITY,
            RTG_RATE_LIMIT_BUCKET_KEY,
            GPTGradingResultResponseSchema,
        )
    except ChatGptVisionException as e:
        if self.request.retries < self.max_retries:
            countdown = (self.request.retries + 1) * 60
            raise self.retry(exc=e, countdown=countdown)

        error_message = 'Exceeded number of max allowed retries'
        await image_prompt_service.update_failed_prompt(image_prompt_batch_process_id, {'error': error_message})
        return
    except (ValueError, KeyError) as e:
        error_message = f'{e.__class__.__name__} error in ChatGPT Vision response. Error: {e}.'
        logger.error(error_message)
        await image_prompt_service.update_failed_prompt(image_prompt_batch_process_id, {'error': error_message})
        return
    except Exception as e:
        error_message = f'Unexpected error happened while processing response. Error: {e}.'
        logger.error(error_message)
        await image_prompt_service.update_failed_prompt(image_prompt_batch_process_id, {'error': error_message})
        return

    if response.is_error:
        await image_prompt_service.update_failed_prompt(image_prompt_batch_process_id, response.data)
    else:
        await image_prompt_service.update_completed_prompt(image_prompt_batch_process_id, response.data)
