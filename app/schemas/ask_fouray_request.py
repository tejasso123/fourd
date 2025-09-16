from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class FourayRequest(BaseModel):
    request_type: str = Field(..., description="Type of the request, always present.", examples=["product_description"])
    additional_data: Dict[str, Any] = Field(..., description="Additional data for the request.",
                                            examples=[{"key": "value"}])

    # class Config:
    #     extra = "allow"
