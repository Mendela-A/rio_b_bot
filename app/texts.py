"""
Bot texts cache.

Texts are loaded from the bot_texts table at startup and refreshed
every 60 seconds in the background, so operator changes take effect
within 1 minute without restarting the bot.

Semantics:
  - value IS NULL   → default_value is used (not overridden by operator)
  - value IS NOT NULL → operator-defined text is used

Usage:
    from app import texts
    await texts.init(pool)          # once, at startup
    texts.get("menu.greeting")      # sync, anywhere in handlers
    texts.get("booking.success", id=42)  # with format args
"""

import asyncio
import logging

import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_cache: dict[str, str] = {}


def get(key: str, **kwargs) -> str:
    value = _cache.get(key, key)
    return value.format(**kwargs) if kwargs else value


async def init(pool: asyncpg.Pool) -> None:
    global _pool
    _pool = pool
    await _reload()
    asyncio.create_task(_refresh_loop())


async def _reload() -> None:
    if _pool is None:
        return
    try:
        rows = await _pool.fetch("SELECT key, COALESCE(value, default_value) AS value FROM bot_texts")
        _cache.update({r["key"]: r["value"] for r in rows if r["value"] is not None})
    except Exception as e:
        logger.error("Failed to reload bot_texts: %s", e)


async def _refresh_loop() -> None:
    while True:
        await asyncio.sleep(60)
        await _reload()
