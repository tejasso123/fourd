from .base_service import BaseService
from app.services.blog_agent_service import ask_fouray_blog_stream, ask_fouray_blog


class BlogService(BaseService):
    async def process(self, drive_service, **data):
        return await ask_fouray_blog(drive_service, **data)

    async def stream_process(self, drive_service, **data):
        async for chunk in ask_fouray_blog_stream(drive_service, **data):
            yield chunk
