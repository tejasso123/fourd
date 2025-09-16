from pydantic import BaseModel, Field
from typing import Dict, Any


class UserCreateRequest(BaseModel):
    request_type: str = Field(..., description="Type of the request, always present.")
    additional_data: Dict[str, Any] = Field(..., description="Additional data for the request.",
                                            examples=[
                                                {"email": "abc@example.com", "first_name": "John", "last_name": "Doe"}])
