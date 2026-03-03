"""
Bot texts cache.

Texts are loaded from the bot_texts table at startup and refreshed
every 60 seconds in the background, so operator changes take effect
within 1 minute without restarting the bot.

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

# key → (default_value, hint_for_operator)
_REGISTRY: dict[str, tuple[str, str]] = {
    "menu.greeting": (
        "Вітаємо у дитячому розважальному центрі «РІО» 💛\n"
        "Раді бачити вас! Оберіть, будь ласка, що вас цікавить:",
        "Привітання при /start",
    ),
    "booking.ask_name": (
        "📝 Введіть прізвище та ім'я:",
        "Запит імені (крок 1)",
    ),
    "booking.ask_phone": (
        "📱 Введіть номер телефону або натисніть кнопку нижче:",
        "Запит телефону (крок 2)",
    ),
    "booking.ask_children": (
        "👶 Скільки дітей буде на святі?",
        "Запит кількості дітей (крок 3)",
    ),
    "booking.ask_date": (
        "📅 Оберіть дату:",
        "Запит дати (крок 4)",
    ),
    "booking.success": (
        "✅ Бронювання #{id} прийнято!\n\nМи зв'яжемося з вами для підтвердження.",
        "Підтвердження бронювання  —  {id} буде замінено на номер",
    ),
    "booking.cancelled": (
        "Бронювання скасовано.",
        "Повідомлення про скасування",
    ),
    "cart.added": (
        "✅ Додано до кошика!",
        "Спливаюче повідомлення при додаванні послуги",
    ),
    "cart.empty": (
        "🛒 Кошик порожній.",
        "Повідомлення про порожній кошик",
    ),
}

_pool: asyncpg.Pool | None = None
_cache: dict[str, str] = {}


def get(key: str, **kwargs) -> str:
    """Return text by key. Falls back to default if not in DB."""
    value = _cache.get(key) or _REGISTRY.get(key, (key,))[0]
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
        rows = await _pool.fetch("SELECT key, value FROM bot_texts")
        _cache.update({r["key"]: r["value"] for r in rows})
    except Exception as e:
        logger.error("Failed to reload bot_texts: %s", e)


async def _refresh_loop() -> None:
    while True:
        await asyncio.sleep(60)
        await _reload()


def registry() -> list[dict]:
    """Return all registered texts with current values (for admin)."""
    return [
        {
            "key": key,
            "hint": hint,
            "value": _cache.get(key, default),
        }
        for key, (default, hint) in _REGISTRY.items()
    ]
