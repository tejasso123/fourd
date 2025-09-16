from .base_service import BaseService
from app.services.legal_gv_agent_service import ask_fouray_legal_gv, ask_fouray_legal_gv_stream


class LegalGlobeViewService(BaseService):
    async def process(self, drive_service, **data):
        return await ask_fouray_legal_gv(drive_service, **data)

    async def stream_process(self, drive_service, **data):
        async for chunk in ask_fouray_legal_gv_stream(drive_service, **data):
            yield chunk
