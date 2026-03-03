import os
from contextlib import asynccontextmanager

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global pool
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "rio"),
        user=os.getenv("DB_USER", "rio_user"),
        password=os.getenv("DB_PASSWORD", "rio_pass"),
        min_size=2,
        max_size=10,
    )


async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()
