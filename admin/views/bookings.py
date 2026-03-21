import logging
import os

import httpx
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db
from shared import templates as _templates

logger = logging.getLogger(__name__)
_BOT_TOKEN = os.getenv("BOT_TOKEN", "")

STATUS_TRANSITIONS = {
    "confirm": "confirmed",
    "cancel":  "cancelled",
    "reopen":  "new",
}


class BookingsView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Бронювання",
            icon="fa fa-calendar-check",
            path="/bookings",
            methods=["GET", "POST"],
            name="bookings",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        section = request.query_params.get("section", "bookings")
        status_filter = request.query_params.get("status", "")
        period_filter = request.query_params.get("period", "")

        bookings_where = "WHERE b.status = $1" if status_filter else ""
        bookings_params = [status_filter] if status_filter else []

        period_where = ""
        if period_filter == "today":
            period_where = "WHERE created_at::date = CURRENT_DATE"
        elif period_filter == "week":
            period_where = "WHERE created_at >= date_trunc('week', NOW())"

        async with db.pool.acquire() as conn:
            bookings_count = await conn.fetchval("SELECT COUNT(*) FROM bookings")
            inquiries_count = await conn.fetchval("SELECT COUNT(*) FROM inquiries")

            if section == "inquiries":
                bookings = []
                items_rows = []
                inquiries = await conn.fetch(
                    f"""
                    SELECT id, full_name, phone, service_name, created_at
                    FROM inquiries
                    {period_where}
                    ORDER BY created_at DESC
                    """
                )
            else:
                bookings = await conn.fetch(
                    f"""
                    SELECT b.id, b.full_name, b.phone, b.children_count,
                           b.adults_count, b.birthday_person_name, b.birthday_person_date,
                           b.booking_date, b.status, b.created_at
                    FROM bookings b
                    {bookings_where}
                    ORDER BY b.created_at DESC
                    """,
                    *bookings_params,
                )
                items_rows = await conn.fetch(
                    """
                    SELECT booking_id, service_name, price, quantity
                    FROM booking_items
                    WHERE booking_id = ANY($1::int[])
                    """,
                    [r["id"] for r in bookings],
                )
                inquiries = []

        items_by_booking: dict[int, list] = {}
        for row in items_rows:
            items_by_booking.setdefault(row["booking_id"], []).append(dict(row))

        data = []
        for b in bookings:
            entry = dict(b)
            entry["services"] = items_by_booking.get(b["id"], [])
            entry["total"] = sum(
                (i["price"] or 0) * i["quantity"] for i in entry["services"] if i["price"]
            )
            data.append(entry)

        return _templates.TemplateResponse(
            "bookings.html", {
                "request": request,
                "section": section,
                "bookings": data,
                "inquiries": [dict(r) for r in inquiries],
                "bookings_count": bookings_count,
                "inquiries_count": inquiries_count,
                "status_filter": status_filter,
                "period_filter": period_filter,
            }
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        action = form.get("_action", "")
        bid = int(form.get("id") or 0)

        new_status = STATUS_TRANSITIONS.get(action)
        if bid and new_status:
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE bookings SET status=$1 WHERE id=$2", new_status, bid
                )
                row = await conn.fetchrow(
                    "SELECT telegram_id, booking_date FROM bookings WHERE id=$1", bid
                )
            logger.info(
                "User %s changed booking #%d to %s",
                request.session.get("username"), bid, new_status,
            )
            if row:
                await _notify_client(row["telegram_id"], bid, row["booking_date"], new_status)

        return RedirectResponse("/admin/bookings", status_code=303)


async def _notify_client(telegram_id: int, booking_id: int, booking_date, new_status: str) -> None:
    if not _BOT_TOKEN:
        return
    date_str = booking_date.strftime("%d.%m.%Y")
    if new_status == "confirmed":
        text = (
            f"✅ Ваше бронювання #{booking_id} на {date_str} підтверджено!\n"
            f"Чекаємо вас! 🎉"
        )
    elif new_status == "cancelled":
        text = (
            f"❌ Ваше бронювання #{booking_id} на {date_str} скасовано.\n"
            f"Зверніться до нас для уточнень."
        )
    else:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{_BOT_TOKEN}/sendMessage",
                json={"chat_id": telegram_id, "text": text},
            )
    except httpx.HTTPError as e:
        logger.error("HTTP error notifying client %s: %s", telegram_id, e)
    except Exception as e:
        logger.error("Failed to notify client %s: %s", telegram_id, e)
