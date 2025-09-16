from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.session import async_engine

AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
