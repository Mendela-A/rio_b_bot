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


async def ensure_default_admin() -> None:
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    username = os.getenv("ADMIN_USER", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin")
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM admin_users")
        if count == 0:
            hashed = pwd_ctx.hash(password)
            await conn.execute(
                "INSERT INTO admin_users (username, password_hash) VALUES ($1, $2)",
                username, hashed,
            )


async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    await ensure_default_admin()
    yield
    await close_pool()
