from fastapi import APIRouter, Depends
import logging
import time
from app.core.validators import validate_request, ASK_FOURAY_RULES
from app.schemas import FourayRequest, FourayResponse
from app.api.deps import require_auth
from app.services import get_google_drive_service_for_system, ServiceFactory
from app.core.exceptions import BadRequestException
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.post("/fouray", response_model=FourayResponse, dependencies=[Depends(require_auth)],
             description="Handles Fouray application requests", summary="Process Fouray request")
async def ask_fouray_app(request: FourayRequest):
    additional_data = request.additional_data or {}

    try:
        # Validate request
        missing_fields, extra_fields = validate_request(request.request_type, additional_data, ASK_FOURAY_RULES)

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

        service = ServiceFactory.get_service(request.request_type)

        if "streaming" in additional_data and additional_data["streaming"]:
            # ask the fouray model
            async def event_stream():
                async for chunk in service.stream_process(drive_service, **additional_data):
                    yield f"data: {chunk}\n\n"  # Server-Sent Events format Working

            return StreamingResponse(event_stream(), media_type="text/event-stream",
                                     headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
        else:
            # ask the fouray model
            response = await service.process(drive_service, **additional_data)
            if response:
                return FourayResponse(data=response)

    except Exception as e:
        logging.error(f"Error in ask_fouray_app: {str(e)}")
        raise e
