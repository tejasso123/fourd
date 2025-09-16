from pydantic import BaseModel, Field
from typing import Dict, Any


class TranslateRequest(BaseModel):
    request_type: str = Field(..., description="Type of the request, always present.", examples=["language_translate"])
    additional_data: Dict[str, Any] = Field(..., description="Additional data for the request.",
                                            examples=[{"key": "value"}])
