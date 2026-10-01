import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
import redis.asyncio as redis

from dev.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    client: redis.Redis | None = None

cache_manager = CacheManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage Redis connection lifecycle."""
    logger.info("Connecting to Redis at %s:%d", settings.REDIS_HOST, settings.REDIS_PORT)
    cache_manager.client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    
    yield
    
    if cache_manager.client is not None:
        await cache_manager.client.aclose()
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis:
    """Dependency to get the Redis instance."""
    if cache_manager.client is None:
        raise RuntimeError("Redis is not initialized")
    return cache_manager.client
