from pydantic import BaseModel, Field


class WebSiteUploadResponse(BaseModel):
    message: str = Field(..., examples=["Website processing started successfully"])
