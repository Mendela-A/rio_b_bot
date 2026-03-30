import asyncpg


async def upsert_user(pool: asyncpg.Pool, telegram_id: int, first_name: str | None, username: str | None) -> None:
    await pool.execute(
        """
        INSERT INTO users (telegram_id, first_name, username, last_seen_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (telegram_id) DO UPDATE
            SET first_name   = EXCLUDED.first_name,
                username     = EXCLUDED.username,
                last_seen_at = NOW()
        """,
        telegram_id, first_name, username,
    )


async def get_all_active_user_ids(pool: asyncpg.Pool) -> list[int]:
    rows = await pool.fetch("SELECT telegram_id FROM users WHERE is_active = TRUE")
    return [r["telegram_id"] for r in rows]


async def get_menu_message_id(pool: asyncpg.Pool, telegram_id: int) -> int | None:
    return await pool.fetchval(
        "SELECT menu_message_id FROM users WHERE telegram_id = $1", telegram_id
    )


async def set_menu_message_id(pool: asyncpg.Pool, telegram_id: int, message_id: int) -> None:
    await pool.execute(
        "UPDATE users SET menu_message_id = $1 WHERE telegram_id = $2",
        message_id, telegram_id,
    )
