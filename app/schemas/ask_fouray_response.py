from pydantic import BaseModel
from typing import Any


class FourayResponse(BaseModel):
    data: Any
