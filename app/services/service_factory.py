from .services_map import SERVICES_MAP
from .base_service import BaseService
from app.core.exceptions import BadRequestException


class ServiceFactory:
    @staticmethod
    def get_service(request_type: str) -> BaseService:
        service = SERVICES_MAP.get(request_type.lower())
        if not service:
            raise BadRequestException(f"Service '{request_type}' not found.")
        return service
