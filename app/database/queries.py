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


# --- Inquiries (quick booking) ---

async def create_inquiry(
    pool: asyncpg.Pool,
    telegram_id: int,
    full_name: str,
    phone: str,
    service_id: int,
    service_name: str,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO inquiries (telegram_id, full_name, phone, service_id, service_name)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        telegram_id,
        full_name,
        phone,
        service_id,
        service_name,
    )
    return row["id"]


# --- Cart ---

async def cart_add(pool: asyncpg.Pool, telegram_id: int, service_id: int) -> None:
    await pool.execute(
        """
        INSERT INTO cart_items (telegram_id, service_id, quantity)
        VALUES ($1, $2, 1)
        ON CONFLICT (telegram_id, service_id) DO UPDATE SET quantity = cart_items.quantity + 1
        """,
        telegram_id,
        service_id,
    )


async def cart_get(pool: asyncpg.Pool, telegram_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT ci.service_id, ci.quantity, s.name, s.price
        FROM cart_items ci
        JOIN services s ON ci.service_id = s.id
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


# --- Bookings ---

async def get_user_bookings(pool: asyncpg.Pool, telegram_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT b.id, b.booking_date, b.status, b.children_count,
               COALESCE(
                   string_agg(bi.service_name, ', ' ORDER BY bi.id),
                   ''
               ) AS services_summary
        FROM bookings b
        LEFT JOIN booking_items bi ON bi.booking_id = b.id
        WHERE b.telegram_id = $1
        GROUP BY b.id
        ORDER BY b.booking_date DESC
        LIMIT 10
        """,
        telegram_id,
    )



async def create_booking(
    pool: asyncpg.Pool,
    telegram_id: int,
    full_name: str,
    phone: str,
    children_count: int,
    booking_date: str,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO bookings (telegram_id, full_name, phone, children_count, booking_date)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        telegram_id,
        full_name,
        phone,
        children_count,
        booking_date,
    )
    return row["id"]


async def create_booking_items(
    pool: asyncpg.Pool, booking_id: int, cart_items: list[asyncpg.Record]
) -> None:
    await pool.executemany(
        """
        INSERT INTO booking_items (booking_id, service_id, service_name, price, quantity)
        VALUES ($1, $2, $3, $4, $5)
        """,
        [
            (booking_id, item["service_id"], item["name"], item["price"], item["quantity"])
            for item in cart_items
        ],
    )
