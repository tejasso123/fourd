from .base_service import BaseService
from .dosha_quiz_agent_service import ask_fouray_dosha_quiz_stream


class DoshaQuizService(BaseService):
    async def process(self, drive_service, **data):
        raise NotImplementedError("The 'process' method is not implemented for dosha quiz.")

    async def stream_process(self, drive_service, **data):
        async for chunk in ask_fouray_dosha_quiz_stream(drive_service, **data):
            yield chunk
