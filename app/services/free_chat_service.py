from .base_service import BaseService
from app.services.free_chat_agent_service import ask_fouray_free_chat, ask_fouray_free_chat_stream


class FreeChatService(BaseService):
    async def process(self, drive_service, **data):
        return await ask_fouray_free_chat(drive_service, **data)

    async def stream_process(self, drive_service, **data):
        async for chunk in ask_fouray_free_chat_stream(drive_service, **data):
            yield chunk
