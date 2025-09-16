from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from .exceptions import APIException


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Generic handler for unexpected exceptions
        return JSONResponse(
            status_code=500,
            content={
                "error": "An unexpected error occurred.",
                "details": str(exc),
                "status_code": 500,
                "path": request.url.path,
                "method": request.method
            },
        )
