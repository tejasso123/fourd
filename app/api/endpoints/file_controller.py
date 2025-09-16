import base64
import aiofiles
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from typing import List, Dict, Any
from app.api.deps import require_auth
from app.core.exceptions import BadRequestException
from app.schemas import FileUploadResponse, FileUploadRequest
from app.utils.file_helper import is_allowed_file, save_file, remove_file
import json
from app.core.validators import validate_request, FILE_UPLOAD_RULES
from app.tasks import process_file_task

router = APIRouter()


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_auth)],
    response_model=FileUploadResponse,
    summary="Upload and Process Files based on request type",
    description="Uploads multiple files, validates them, and initiates async processing tasks."
)
async def upload_file(
        request_json: str = Form(..., description="Request metadata in JSON format"),
        files: List[UploadFile] = File(..., description="Files to upload"),
        current_user: Dict[str, Any] = Depends(require_auth)
):
    # Parse the incoming JSON request
    try:
        request_data = json.loads(request_json)
        request = FileUploadRequest(**request_data)
    except json.JSONDecodeError:
        raise BadRequestException("Invalid JSON format for request.")
    except Exception as e:
        raise BadRequestException(f"Invalid request data: {str(e)}")

    try:
        # Extract additional data for validation
        additional_data = request.additional_data or {}

        # Validate request
        missing_fields, extra_fields = validate_request(request.request_type, additional_data, FILE_UPLOAD_RULES)

        if missing_fields:
            raise BadRequestException(
                f"Missing required fields for {request.request_type}: {', '.join(missing_fields)}")
        if extra_fields:
            raise BadRequestException(f"Invalid fields for {request.request_type}: {', '.join(extra_fields)}")

        if not files:
            raise BadRequestException("No file part in the request")

        if len(files) == 0:
            raise BadRequestException("No file selected")

        dim_3_value = current_user.dim3

        # Validate all files before processing
        for file in files:
            if file.filename == '':
                raise BadRequestException("No selected file")

            if not is_allowed_file(file.filename):
                raise BadRequestException(f"Unsupported file type: {file.filename}")

            file_extension = file.filename.rsplit('.', 1)[1].lower()
            path_name = await save_file(file)

            try:
                # Read the content asynchronously
                async with aiofiles.open(path_name, "rb") as f:
                    file_bytes = await f.read()
                    file_content = base64.b64encode(file_bytes).decode("utf-8")

                    # Initiate async background task
                process_file_task.delay(
                    file_content=file_content, file_path=path_name, file_extension=file_extension,
                    is_file_already_saved=True,
                    filters=additional_data,
                    dim3_value=dim_3_value
                )
            except Exception as e:
                raise e
            finally:
                # Remove temporary file
                await remove_file(path_name)

        return FileUploadResponse(message="Files processing started successfully")

    except Exception as e:
        raise e
