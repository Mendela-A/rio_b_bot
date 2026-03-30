from datetime import date

import asyncpg


def _resolve_item_price(item) -> float | None:
    ppc = item.get("price_per_child")
    if ppc:
        return ppc * item["quantity"]
    return item["price"]


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
    adults_count: int,
    birthday_person_name: str,
    birthday_person_date,
    booking_date: str,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO bookings (
            telegram_id, full_name, phone, children_count,
            adults_count, birthday_person_name, birthday_person_date,
            booking_date
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        telegram_id,
        full_name,
        phone,
        children_count,
        adults_count,
        birthday_person_name,
        birthday_person_date,
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
            (booking_id, item["service_id"], item["name"], _resolve_item_price(item), item["quantity"])
            for item in cart_items
        ],
    )


async def get_booking_items(pool: asyncpg.Pool, booking_id: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT service_id, service_name AS name, price, quantity FROM booking_items WHERE booking_id=$1 ORDER BY id",
        booking_id,
    )


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
        [(change_request_id, item["service_id"], item["name"], _resolve_item_price(item), item["quantity"])
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
            if req is None:
                return
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
