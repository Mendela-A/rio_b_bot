import asyncpg


async def get_ai_qa_pairs(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT question, answer FROM ai_qa_pairs WHERE is_active=TRUE ORDER BY sort_order, id"
    )


async def get_ai_history(pool: asyncpg.Pool, telegram_id: int, limit: int = 20) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT role, content FROM ("
        "  SELECT role, content, created_at FROM ai_chat_history"
        "  WHERE telegram_id=$1 ORDER BY created_at DESC LIMIT $2"
        ") t ORDER BY created_at",
        telegram_id, limit,
    )


async def append_ai_history(pool: asyncpg.Pool, telegram_id: int, role: str, content: str) -> None:
    await pool.execute(
        "INSERT INTO ai_chat_history (telegram_id, role, content) VALUES ($1,$2,$3)",
        telegram_id, role, content,
    )


async def clear_ai_history(pool: asyncpg.Pool, telegram_id: int) -> None:
    await pool.execute("DELETE FROM ai_chat_history WHERE telegram_id=$1", telegram_id)


async def get_ai_history_last_age_hours(pool: asyncpg.Pool, telegram_id: int) -> float | None:
    """Повертає вік останнього повідомлення в годинах, або None якщо історії нема."""
    val = await pool.fetchval(
        "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(created_at))) / 3600"
        " FROM ai_chat_history WHERE telegram_id=$1",
        telegram_id,
    )
    return float(val) if val is not None else None


async def trim_ai_history(pool: asyncpg.Pool, telegram_id: int, limit: int) -> None:
    """Видаляє старі повідомлення, залишаючи тільки `limit` останніх."""
    await pool.execute(
        "DELETE FROM ai_chat_history WHERE telegram_id=$1 AND id NOT IN ("
        "  SELECT id FROM ai_chat_history WHERE telegram_id=$1"
        "  ORDER BY created_at DESC LIMIT $2"
        ")",
        telegram_id, limit,
    )


async def log_ai_usage(
    pool: asyncpg.Pool,
    telegram_id: int,
    input_tokens: int,
    output_tokens: int,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
    response_ms: int | None = None,
    model: str | None = None,
) -> None:
    await pool.execute(
        "INSERT INTO ai_usage_log "
        "(telegram_id, input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, response_ms, model) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7)",
        telegram_id, input_tokens, output_tokens, cache_write_tokens, cache_read_tokens,
        response_ms, model,
    )


async def get_ai_usage_stats(pool: asyncpg.Pool) -> dict:
    row = await pool.fetchrow(
        "SELECT SUM(input_tokens) AS total_in, SUM(output_tokens) AS total_out, "
        "COUNT(*) AS total_requests, "
        "SUM(cache_write_tokens) AS total_cache_write, SUM(cache_read_tokens) AS total_cache_read "
        "FROM ai_usage_log"
    )
    daily = await pool.fetch(
        "SELECT DATE(created_at) AS day, SUM(input_tokens) AS inp, SUM(output_tokens) AS out, "
        "SUM(cache_write_tokens) AS cache_write, SUM(cache_read_tokens) AS cache_read "
        "FROM ai_usage_log GROUP BY day ORDER BY day DESC LIMIT 14"
    )
    return {"summary": dict(row), "daily": [dict(r) for r in daily]}
