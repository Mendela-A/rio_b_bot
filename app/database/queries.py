from datetime import date

import asyncpg


async def get_services_by_type(pool: asyncpg.Pool, category_type: str) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT s.id, s.name, s.price, s.description
        FROM services s
        JOIN categories c ON s.category_id = c.id
        WHERE c.type = $1 AND s.is_active = true AND s.parent_id IS NULL
        ORDER BY s.sort_order NULLS LAST, s.id
        """,
        category_type,
    )


async def get_child_services(pool: asyncpg.Pool, parent_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT id, name, price, description
        FROM services
        WHERE parent_id = $1 AND is_active = true
        ORDER BY sort_order NULLS LAST, id
        """,
        parent_id,
    )


async def get_service_by_id(pool: asyncpg.Pool, service_id: int) -> asyncpg.Record:
    return await pool.fetchrow(
        """
        SELECT s.id, s.name, s.price, s.description, s.photo_url, c.type as category_type
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


# --- Blocked dates ---

async def get_blocked_dates(pool: asyncpg.Pool) -> set:
    rows = await pool.fetch("SELECT date FROM blocked_dates")
    return {r["date"] for r in rows}


async def get_blocked_weekdays(pool: asyncpg.Pool) -> set[int]:
    row = await pool.fetchrow("SELECT value FROM settings WHERE key = 'blocked_weekdays'")
    if not row or not row["value"]:
        return set()
    return {int(x) for x in row["value"].split(",") if x.strip().isdigit()}


# --- Settings ---

async def get_setting(pool: asyncpg.Pool, key: str, default: str = "") -> str:
    row = await pool.fetchrow("SELECT value FROM settings WHERE key = $1", key)
    return row["value"] if row else default


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
        ON CONFLICT (telegram_id, service_id) DO UPDATE SET quantity = LEAST(cart_items.quantity + 1, 10)
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

async def get_booking_by_id(pool: asyncpg.Pool, booking_id: int) -> asyncpg.Record:
    return await pool.fetchrow(
        "SELECT id, telegram_id, booking_date, status, full_name FROM bookings WHERE id=$1",
        booking_id,
    )


async def update_booking_status(pool: asyncpg.Pool, booking_id: int, status: str) -> None:
    await pool.execute(
        "UPDATE bookings SET status=$1 WHERE id=$2", status, booking_id
    )


async def get_user_bookings(
    pool: asyncpg.Pool, telegram_id: int, *, limit: int = 10
) -> list[asyncpg.Record]:
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
        LIMIT $2
        """,
        telegram_id,
        limit,
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


# --- Admin queries ---

async def get_stats(pool: asyncpg.Pool) -> asyncpg.Record:
    return await pool.fetchrow("""
        SELECT
            COUNT(*)                                      AS total_bookings,
            COUNT(*) FILTER (WHERE status = 'new')       AS count_new,
            COUNT(*) FILTER (WHERE status = 'confirmed') AS count_confirmed,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS count_cancelled,
            (SELECT COUNT(*) FROM inquiries)              AS total_inquiries
        FROM bookings
    """)


async def get_bookings_in_range(
    pool: asyncpg.Pool, date_from: date, date_to: date
) -> list[asyncpg.Record]:
    return await pool.fetch("""
        SELECT b.id, b.full_name, b.phone, b.children_count, b.booking_date, b.status, b.telegram_id,
               COALESCE(string_agg(bi.service_name, ', ' ORDER BY bi.id), '') AS services_summary
        FROM bookings b
        LEFT JOIN booking_items bi ON bi.booking_id = b.id
        WHERE b.booking_date BETWEEN $1 AND $2
        GROUP BY b.id
        ORDER BY b.booking_date ASC, b.id ASC
    """, date_from, date_to)


async def get_bookings_new(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch("""
        SELECT b.id, b.full_name, b.phone, b.children_count, b.booking_date, b.status, b.telegram_id,
               COALESCE(string_agg(bi.service_name, ', ' ORDER BY bi.id), '') AS services_summary
        FROM bookings b
        LEFT JOIN booking_items bi ON bi.booking_id = b.id
        WHERE b.status = 'new'
        GROUP BY b.id
        ORDER BY b.booking_date ASC, b.id ASC
    """)
