from typing import AsyncGenerator

from .base_service import BaseService
from app.services import ask_fouray_product_description_stream


class ProductDescriptionService(BaseService):
    async def process(self, drive_service, **data):
        # return await ask_fouray_product_description_stream(drive_service, **data)
        pass

    async def stream_process(self, drive_service, **kwargs):
        async for chunk in ask_fouray_product_description_stream(drive_service, **kwargs):
            yield chunk
