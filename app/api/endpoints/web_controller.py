from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.core.exceptions import BadRequestException, InternalServerErrorException
from app.core.validators import validate_request, WEB_UPLOAD_RULES
from app.schemas import WebsiteUploadRequest, WebSiteUploadResponse
from app.db.models import User
from app.services.web_service import process_web_urls

router = APIRouter()


@router.post("upload", response_model=WebSiteUploadResponse, summary="Upload Website content",
             description="Uploads website content to the knowledge base", dependencies=[Depends(require_auth)],
             )
async def upload_website_content(request: WebsiteUploadRequest, current_user: User = Depends(require_auth)):
    additional_data = request.additional_data or {}
    try:
        # validate request
        missing_fields, extra_fields = validate_request(request.request_type, additional_data, WEB_UPLOAD_RULES)
        if missing_fields:
            raise BadRequestException(
                f"Missing required fields for {request.request_type}: {', '.join(missing_fields)}")
        if extra_fields:
            raise BadRequestException(f"Invalid fields for {request.request_type}: {', '.join(extra_fields)}")

        dim3_val = current_user.dim3
        url = additional_data.get("url", "")

        # Load the webpage asynchronously
        await process_web_urls(url=url, dim3_value=dim3_val, filters=additional_data)

        return WebSiteUploadResponse(message="Webpage uploaded successfully")


    except Exception as e:
        raise InternalServerErrorException(f"Invalid request data: {str(e)}")
