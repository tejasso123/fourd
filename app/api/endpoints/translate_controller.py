import logging
import time
from fastapi import APIRouter, Depends
from app.api.deps import require_auth
from app.core.exceptions import BadRequestException, InternalServerErrorException
from app.core.validators import validate_request, TRANSLATE_RULES
from app.schemas import TranslateRequest, TranslateResponse
from fastapi.responses import StreamingResponse
from app.services import get_google_drive_service_for_system, ServiceFactory
from app.services.translate_agent_service import translate_content_stream

router = APIRouter()


@router.post("/content", response_model=TranslateResponse,
             dependencies=[Depends(require_auth)],
             description="Translate content to given language and region context", summary="Translate content")
async def translate_content(request: TranslateRequest):
    additional_data = request.additional_data or {}

    try:
        # Validate request
        missing_fields, extra_fields = validate_request(request.request_type, additional_data, TRANSLATE_RULES)

        if missing_fields:
            raise BadRequestException(
                f"Missing required fields for {request.request_type}: {', '.join(missing_fields)}")
        if extra_fields:
            raise BadRequestException(f"Invalid fields for {request.request_type}: {', '.join(extra_fields)}")

        start_time = time.time()
        drive_service = await get_google_drive_service_for_system()
        end_time = time.time()
        time_taken = end_time - start_time
        print(f"Time taken to get drive service: {time_taken:.2f} seconds")

        # ask the fouray model
        async def event_stream():
            async for chunk in translate_content_stream(drive_service, **additional_data):
                yield f"data: {chunk}\n\n"  # Server-Sent Events format Working

        return StreamingResponse(event_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    except Exception as e:
        logging.error(f"Error in ask_fouray_app: {str(e)}")
        raise e
