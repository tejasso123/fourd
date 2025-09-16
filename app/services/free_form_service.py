from .base_service import BaseService
from .free_form_agent_service import ask_fouray_free_form_stream


class FreeFormService(BaseService):
    async def process(self, drive_service, **data):
        raise NotImplementedError("The 'process' method is not implemented for Free form.")

    async def stream_process(self, drive_service, **data):
        async for chunk in ask_fouray_free_form_stream(drive_service, **data):
            yield chunk
