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


# --- Users ---

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
        "SELECT id, telegram_id, booking_date, status, full_name, phone, children_count FROM bookings WHERE id=$1",
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


# --- Booking items ---

async def get_booking_items(pool: asyncpg.Pool, booking_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT service_id, service_name AS name, price, quantity FROM booking_items WHERE booking_id=$1 ORDER BY id",
        booking_id,
    )


# --- Booking change requests ---

async def create_change_request(
    pool: asyncpg.Pool, booking_id: int, proposed_date, proposed_children: int
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO booking_change_requests (booking_id, proposed_date, proposed_children_count)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        booking_id, proposed_date, proposed_children,
    )
    return row["id"]


async def create_change_items(
    pool: asyncpg.Pool, change_request_id: int, items: list[asyncpg.Record]
) -> None:
    await pool.executemany(
        """
        INSERT INTO booking_change_items (change_request_id, service_id, service_name, price, quantity)
        VALUES ($1, $2, $3, $4, $5)
        """,
        [(change_request_id, item["service_id"], item["name"], item["price"], item["quantity"])
         for item in items],
    )


async def get_change_request(pool: asyncpg.Pool, request_id: int) -> asyncpg.Record:
    return await pool.fetchrow(
        "SELECT * FROM booking_change_requests WHERE id=$1",
        request_id,
    )


async def get_change_items(pool: asyncpg.Pool, change_request_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT * FROM booking_change_items WHERE change_request_id=$1 ORDER BY id",
        change_request_id,
    )


async def get_pending_change_for_booking(pool: asyncpg.Pool, booking_id: int) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT id FROM booking_change_requests WHERE booking_id=$1 AND status='pending'",
        booking_id,
    )


async def update_change_request_status(pool: asyncpg.Pool, request_id: int, status: str) -> None:
    await pool.execute(
        "UPDATE booking_change_requests SET status=$1 WHERE id=$2",
        status, request_id,
    )


async def apply_change_request(pool: asyncpg.Pool, request_id: int) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            req = await conn.fetchrow(
                "SELECT booking_id, proposed_date, proposed_children_count FROM booking_change_requests WHERE id=$1",
                request_id,
            )
            booking_id = req["booking_id"]
            await conn.execute(
                "UPDATE bookings SET booking_date=$1, children_count=$2 WHERE id=$3",
                req["proposed_date"], req["proposed_children_count"], booking_id,
            )
            await conn.execute("DELETE FROM booking_items WHERE booking_id=$1", booking_id)
            await conn.execute(
                """
                INSERT INTO booking_items (booking_id, service_id, service_name, price, quantity)
                SELECT $1, service_id, service_name, price, quantity
                FROM booking_change_items WHERE change_request_id=$2
                """,
                booking_id, request_id,
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
