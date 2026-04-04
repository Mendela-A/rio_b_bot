import asyncpg


async def cart_add(pool: asyncpg.Pool, telegram_id: int, service_id: int, quantity: int = 1) -> None:
    await pool.execute(
        """
        INSERT INTO cart_items (telegram_id, service_id, quantity)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id, service_id) DO UPDATE SET quantity = EXCLUDED.quantity
        """,
        telegram_id,
        service_id,
        quantity,
    )


async def cart_get(pool: asyncpg.Pool, telegram_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT ci.service_id, ci.quantity, s.name, s.price, s.price_per_child,
               c.type AS category_type
        FROM cart_items ci
        JOIN services s ON ci.service_id = s.id
        JOIN categories c ON s.category_id = c.id
        WHERE ci.telegram_id = $1
        ORDER BY ci.id
        """,
        telegram_id,
    )


async def cart_remove(pool: asyncpg.Pool, telegram_id: int, service_id: int) -> None:
    await pool.execute(
        "DELETE FROM cart_items WHERE telegram_id = $1 AND service_id = $2",
        telegram_id,
        service_id,
    )


async def cart_clear(pool: asyncpg.Pool, telegram_id: int) -> None:
    await pool.execute(
        "DELETE FROM cart_items WHERE telegram_id = $1",
        telegram_id,
    )
