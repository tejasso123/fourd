from pydantic import BaseModel, Field
from typing import Dict, Any


class WebsiteUploadRequest(BaseModel):
    request_type: str = Field(..., examples=["product_description_file_upload"])
    additional_data: Dict[str, Any] = Field(...,
                                            examples=[{"sku": "1234", "url": "https://www.example.com", "tags": []}])
