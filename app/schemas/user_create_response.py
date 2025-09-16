from pydantic import BaseModel, Field


class UserCreateResponse(BaseModel):
    api_key: str = Field(..., description="API key for the user", examples=["1234567890abcdef"])
    is_success: bool = Field(..., description="Indicates if the user creation was successful", examples=[True])
    error: str = Field(None, description="Error message if the user creation failed", examples=["User already exists"])
