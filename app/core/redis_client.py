import redis.asyncio as redis_async
from functools import lru_cache

from app.core.config import settings


@lru_cache()
def get_redis() -> redis_async.Redis:
    """Get Redis client instance with connection pooling."""
    return redis_async.from_url(settings.redis_url, decode_responses=True)
