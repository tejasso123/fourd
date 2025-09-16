from fastapi import APIRouter
from app.core import settings
from app.api.endpoints import ask_fouray_controller as ask
from app.api.endpoints import file_controller as file
from app.api.endpoints import web_controller as web
from app.api.endpoints import user_controller as user
from app.api.endpoints import translate_controller as translate

api_router = APIRouter(prefix=settings.API_V1_STR)

# api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(ask.router, prefix="/ask", tags=["Ask"])
api_router.include_router(file.router, prefix="/file", tags=["File"])
api_router.include_router(web.router, prefix="/web", tags=["Web"])
api_router.include_router(user.router, prefix="/user", tags=["User"])
api_router.include_router(translate.router, prefix="/translate", tags=["Translate"])
