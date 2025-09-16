from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core import settings

IS_PROD = settings.ENV == "prod"

async_engine = create_async_engine(
    settings.DB_STR,
    echo=not IS_PROD,
    pool_size=5,
    max_overflow=10,
    pool_recycle=600,
    pool_timeout=30,
    pool_pre_ping=True,
    connect_args={"statement_cache_size": 0}
)

# AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


# async def get_async_session() -> AsyncSession:
#     async with AsyncSessionLocal() as session:
#         yield session
