from contextlib import asynccontextmanager
from app.db.session import async_engine
from app.db.models.base import Base
from app.scheduler import start_scheduler
from app.utils import redis_client


@asynccontextmanager
async def lifespan(app):
    try:

        # Startup: initialize database and scheduler
        print("🔵 Starting up: Initializing DB")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await redis_client.connect_async()  # Ensure Redis is connected at startup
        await start_scheduler()  # Start the scheduler
        print("🔵 Starting up: Initializing DB Completed")
        yield  # Yield for app lifecycle
    finally:
        # Shutdown: close database connection
        print("🛑 Shutting down: Closing DB Connection")
        await redis_client.close_async()  # 🚀 Close redis connection properly
        await async_engine.dispose()  # 🚀 Close connection properly
        print("🛑 Shutting down: Closing DB Connection Completed")
