# from contextlib import asynccontextmanager
# from fastapi import FastAPI
# from dotenv import load_dotenv
# import uvicorn
# import os
#
# from app.core import settings
# from app.api.router import api_router
# from app.db.session import engine, Base
# from app.tasks.scheduler import start_scheduler
#
# # Load environment variables
# load_dotenv()
#
#
# # Initialize lifespan manager
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Initialize database tables
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     # Start scheduled jobs
#     start_scheduler()
#
#     yield  # Wait here until the app is shutting down
#
#     # Cleanup on shutdown (optional)
#     await engine.dispose()  # Close DB connections if using SQLAlchemy Async
#
#
# app = FastAPI(
#     title=settings.PROJECT_NAME,
#     version=settings.VERSION,
#     lifespan=lifespan
# )
#
# # Register API routes
# app.include_router(api_router, prefix=settings.API_V1_STR)
#
#
# # Root endpoint
# @app.get("/", tags=["Root"])
# async def read_root():
#     return {"message": "Welcome to the Fouray"}
#
#
# # Application entry point
# if __name__ == "__main__":
#     uvicorn.run(
#         "main:app",
#         host=os.getenv('APP_HOST', '0.0.0.0'),
#         port=int(os.getenv('APP_PORT', 8000)),
#         reload=os.getenv('APP_RELOAD', 'True').lower() == 'true'
#     )


from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
from fastapi.middleware.cors import CORSMiddleware

from app.core import settings
from app.core import lifespan
from app.api.router import api_router
from app.core import register_exception_handlers

ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS.split(",")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, description=settings.DESCRIPTION,
              lifespan=lifespan)

register_exception_handlers(app)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type"]
)

app.include_router(api_router)

HTML_FILE_PATH = os.path.join(os.path.dirname(__file__), "static/welcome.html")

TEMP_FOLDER = './temp_files'
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)


# Root route
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root():
    return FileResponse(HTML_FILE_PATH)
