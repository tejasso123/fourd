from fastapi import UploadFile, File
from pydantic import BaseModel, Field
from typing import Dict, Any, List


class FileUploadRequest(BaseModel):
    request_type: str = Field(..., description="Type of the request, always present.", examples=["product_description"])
    additional_data: Dict[str, Any] = Field(..., description="Additional data for the request.",
                                            examples=[{"key": "value"}])
