from fastapi import HTTPException, status


class APIException(HTTPException):
    """Base class for custom API exceptions."""

    def __init__(self, detail: str, status_code: int):
        super().__init__(status_code=status_code, detail=detail)


class AuthenticationException(APIException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationException(APIException):
    """Raised when user is not authorized to access resource."""

    def __init__(self, detail: str = "Not authorized to access this resource"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class ResourceNotFoundException(APIException):
    """Raised when requested resource is not found."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class BadRequestException(APIException):
    """Raised when request validation fails or is bad."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class InternalServerErrorException(APIException):
    """Raised when an unexpected error occurs."""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceUnavailableException(APIException):
    """Raised when a service is unavailable."""

    def __init__(self, detail: str = "Service unavailable"):
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
      