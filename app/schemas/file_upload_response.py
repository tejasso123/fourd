from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    message: str = Field(..., examples=["Files processing started successfully"])
