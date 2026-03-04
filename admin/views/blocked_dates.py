import os
from datetime import date

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


class BlockedDatesView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Налашт. дат",
            icon="fa fa-calendar",
            path="/blocked-dates",
            methods=["GET", "POST"],
            name="blocked_dates",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT date, reason FROM blocked_dates ORDER BY date"
            )
            settings = {
                r["key"]: r["value"]
                for r in await conn.fetch(
                    "SELECT key, value FROM settings WHERE key IN ('blocked_weekdays','booking_days_ahead')"
                )
            }

        blocked_weekdays = set()
        if settings.get("blocked_weekdays"):
            blocked_weekdays = {
                int(x) for x in settings["blocked_weekdays"].split(",")
                if x.strip().isdigit()
            }
        today = date.today()
        return _templates.TemplateResponse(
            "blocked_dates.html", {
                "request": request,
                "upcoming": [dict(r) for r in rows if r["date"] >= today],
                "past":     [dict(r) for r in rows if r["date"] < today],
                "blocked_weekdays": blocked_weekdays,
                "days_ahead": settings.get("booking_days_ahead", "14"),
            }
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        action = form.get("_action", "")
        async with db.pool.acquire() as conn:
            if action == "days":
                val = (form.get("booking_days_ahead") or "14").strip()
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('booking_days_ahead', $1) "
                    "ON CONFLICT (key) DO UPDATE SET value = $1",
                    val,
                )
            elif action == "weekdays":
                selected = form.getlist("weekday")
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('blocked_weekdays', $1) "
                    "ON CONFLICT (key) DO UPDATE SET value = $1",
                    ",".join(selected),
                )
            elif action == "add":
                raw = (form.get("date") or "").strip()
                reason = (form.get("reason") or "").strip()
                if raw:
                    await conn.execute(
                        "INSERT INTO blocked_dates (date, reason) VALUES ($1, $2) "
                        "ON CONFLICT (date) DO UPDATE SET reason = $2",
                        date.fromisoformat(raw), reason,
                    )
            elif action == "delete":
                raw = (form.get("date") or "").strip()
                if raw:
                    await conn.execute(
                        "DELETE FROM blocked_dates WHERE date = $1",
                        date.fromisoformat(raw),
                    )
        return RedirectResponse("/admin/blocked-dates", status_code=303)
