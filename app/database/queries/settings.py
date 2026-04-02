from datetime import date as _date

import asyncpg


async def get_setting(pool: asyncpg.Pool, key: str, default: str = "") -> str:
    row = await pool.fetchrow("SELECT value FROM settings WHERE key = $1", key)
    return row["value"] if row else default


async def get_entry_tariff(pool: asyncpg.Pool, booking_date) -> float:
    """Повертає ціну за дитину для дати (будні або вихідні)."""
    if isinstance(booking_date, str):
        booking_date = _date.fromisoformat(booking_date)
    is_weekend = booking_date.isoweekday() >= 6
    key = "tariff_weekend" if is_weekend else "tariff_weekday"
    val = await get_setting(pool, key, "0")
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


async def get_blocked_dates(pool: asyncpg.Pool) -> set:
    rows = await pool.fetch("SELECT date FROM blocked_dates")
    return {r["date"] for r in rows}


async def get_blocked_weekdays(pool: asyncpg.Pool) -> set[int]:
    row = await pool.fetchrow("SELECT value FROM settings WHERE key = 'blocked_weekdays'")
    if not row or not row["value"]:
        return set()
    return {int(x) for x in row["value"].split(",") if x.strip().isdigit()}


async def create_inquiry(
    pool: asyncpg.Pool,
    telegram_id: int,
    full_name: str,
    phone: str,
    service_id: int,
    service_name: str,
    children_count: int | None = None,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO inquiries (telegram_id, full_name, phone, service_id, service_name, children_count)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        telegram_id,
        full_name,
        phone,
        service_id,
        service_name,
        children_count,
    )
    return row["id"]
