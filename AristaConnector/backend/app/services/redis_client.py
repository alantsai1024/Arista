import redis.asyncio as redis
import os
from typing import Optional

_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(redis_url, decode_responses=False)
    return _redis_client


async def close_redis_client():
    """Close Redis client"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
