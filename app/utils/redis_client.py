from redis.asyncio import Redis
from typing import Optional
from app.core import settings


class AsyncRedisClient:
    def __init__(self):
        redis_url = settings.REDIS_URL
        self.client = None
        self.redis_url = redis_url
        self.CACHE_EXPIRY_SECONDS = settings.CACHE_EXPIRY_SECONDS  # Default to 1 month

    async def connect_async(self):
        """
        Establish a connection to Redis.
        """
        if self.client is None:
            self.client = await Redis.from_url(self.redis_url, decode_responses=True)

    async def set_value_async(self, key: str, value: str):
        """
        Store a value in Redis with an expiry time.
        Args:
            key (str): The key for the cached value.
            value (str): The value to store.
        """
        try:
            await self.client.setex(key, self.CACHE_EXPIRY_SECONDS, value)
        except Exception as e:
            print(f"❌ Error setting value in Redis: {str(e)}")

    async def get_value_async(self, key: str) -> Optional[str]:
        """
        Retrieve a value from Redis.
        Args:
            key (str): The key to fetch.
        Returns:
            Optional[str]: The cached value, or None if not found or an error occurs.
        """
        try:
            cached_value = await self.client.get(key)
            return cached_value if cached_value else None
        except Exception as e:
            print(f"❌ Error fetching value from Redis: {str(e)}")
            return None

    async def close_async(self):
        """
        Close the Redis connection.
        """
        if self.client:
            await self.client.close()
            self.client = None


# Create a global instance
redis_client = AsyncRedisClient()
