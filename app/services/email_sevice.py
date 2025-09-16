from .base_service import BaseService
from app.services.email_agent_service import ask_fouray_email, ask_fouray_email_stream


class EmailService(BaseService):
    async def process(self, drive_service, **data):
        return await ask_fouray_email(drive_service, **data)

    async def stream_process(self, drive_service, **data):
        async for chunk in ask_fouray_email_stream(drive_service, **data):
            yield chunk
