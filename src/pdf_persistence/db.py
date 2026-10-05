import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pymongo
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from dev.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


db_manager = DatabaseManager()


async def setup_indexes() -> None:
    if db_manager.db is not None:
        collection = db_manager.db["documents"]
        # Create a unique index on checksum to prevent duplicates
        await collection.create_index(
            [("checksum", pymongo.ASCENDING)],
            unique=True,
            name="idx_unique_checksum",
        )
        logger.info("MongoDB indexes verified/created")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage MongoDB and Redis connection lifecycle."""
    from pdf_persistence.cache import lifespan as cache_lifespan

    logger.info("Connecting to MongoDB at %s", settings.MONGO_URI)
    db_manager.client = AsyncIOMotorClient(settings.MONGO_URI)
    db_manager.db = db_manager.client[settings.MONGO_DB_NAME]

    await setup_indexes()

    async with cache_lifespan(app):
        yield

    if db_manager.client is not None:
        db_manager.client.close()
        logger.info("MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    """Dependency to get the database instance."""
    if db_manager.db is None:
        raise RuntimeError("Database is not initialized")
    return db_manager.db
