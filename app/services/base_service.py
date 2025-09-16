from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class BaseService(ABC):

    @abstractmethod
    async def process(self, drive_service, **kwargs) -> Any:
        pass

    @abstractmethod
    async def stream_process(self, drive_service, **kwargs) -> AsyncGenerator[str, None]:
        """Streaming version of process, yielding chunks of JSON strings."""
        pass
