import logging
import asyncpg
from app.config import Config

logger = logging.getLogger(__name__)


async def create_pool(config: Config) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        host=config.db_host,
        port=config.db_port,
        database=config.db_name,
        user=config.db_user,
        password=config.db_password,
    )
    logger.info("Database pool created")
    return pool


async def close_pool(pool: asyncpg.Pool) -> None:
    await pool.close()
    logger.info("Database pool closed")
