import asyncpg


async def get_services_by_type(pool: asyncpg.Pool, category_type: str) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT s.id, s.name, s.price, s.description
        FROM services s
        JOIN categories c ON s.category_id = c.id
        WHERE c.type = $1 AND s.is_active = true
        ORDER BY s.sort_order
        """,
        category_type,
    )


async def get_info_pages(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT id, title FROM info_pages ORDER BY sort_order"
    )


async def get_info_page_by_id(pool: asyncpg.Pool, page_id: int) -> asyncpg.Record:
    return await pool.fetchrow(
        "SELECT title, content FROM info_pages WHERE id = $1",
        page_id,
    )
