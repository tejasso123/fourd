from fastapi import APIRouter, Depends
import logging
from app.schemas import UserCreateRequest, UserCreateResponse
from app.core.validators import validate_request, USER_CREATE_RULES
from app.api.deps import require_auth
from app.core.exceptions import BadRequestException
from app.services.user_service import create_user_and_generate_api_key

router = APIRouter()


@router.post("/create", response_model=UserCreateResponse, dependencies=[Depends(require_auth)],
             description="User create request", summary="Process Fouray request", include_in_schema=False)
async def ask_fouray_app(request: UserCreateRequest):
    additional_data = request.additional_data or {}

    try:
        # Validate request
        missing_fields, extra_fields = validate_request(request.request_type, additional_data, USER_CREATE_RULES)

        if missing_fields:
            raise BadRequestException(
                f"Missing required fields for {request.request_type}: {', '.join(missing_fields)}")
        if extra_fields:
            raise BadRequestException(f"Invalid fields for {request.request_type}: {', '.join(extra_fields)}")

        response = await create_user_and_generate_api_key(**additional_data)

        if response:
            return UserCreateResponse(api_key=response, is_success=True, error="")

    except Exception as e:
        logging.error(f"Error in ask_fouray_app: {str(e)}")
        return UserCreateResponse(api_key="", is_success=False, error=f"Error in ask_fouray_app: {str(e)}")
