from pydantic import BaseModel
from typing import Any


class TranslateResponse(BaseModel):
    data: Any
