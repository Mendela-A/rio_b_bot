import asyncpg


async def get_services_by_type(pool: asyncpg.Pool, category_type: str) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT s.id, s.name, s.price, s.description
        FROM services s
        JOIN categories c ON s.category_id = c.id
        WHERE c.type = $1 AND s.is_active = true AND s.parent_id IS NULL
        ORDER BY s.sort_order
        """,
        category_type,
    )


async def get_child_services(pool: asyncpg.Pool, parent_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT id, name, price, description
        FROM services
        WHERE parent_id = $1 AND is_active = true
        ORDER BY sort_order
        """,
        parent_id,
    )


async def get_service_by_id(pool: asyncpg.Pool, service_id: int) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        SELECT s.id, s.name, s.price, s.description, c.type as category_type
        FROM services s
        JOIN categories c ON s.category_id = c.id
        WHERE s.id = $1
        """,
        service_id,
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
