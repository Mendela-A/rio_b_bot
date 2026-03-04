from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView
import os
import db

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)

_SETTINGS_META = {
    "booking_days_ahead": {
        "label": "Кількість днів для вибору дати бронювання",
        "hint": "Скільки днів вперед клієнт може обрати при бронюванні (зараз: 14)",
        "type": "number",
        "min": 1,
        "max": 90,
    },
}


class SettingsView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Налаштування",
            icon="fa fa-cog",
            path="/settings",
            methods=["GET", "POST"],
            name="settings",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT key, value FROM settings")
        values = {r["key"]: r["value"] for r in rows}

        items = []
        for key, meta in _SETTINGS_META.items():
            items.append({
                "key": key,
                "value": values.get(key, ""),
                **meta,
            })

        return _templates.TemplateResponse(
            "settings.html", {"request": request, "items": items, "saved": request.query_params.get("saved")}
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        async with db.pool.acquire() as conn:
            for key in _SETTINGS_META:
                val = (form.get(key) or "").strip()
                if val:
                    await conn.execute(
                        "INSERT INTO settings (key, value) VALUES ($1, $2) "
                        "ON CONFLICT (key) DO UPDATE SET value = $2",
                        key, val,
                    )
        return RedirectResponse("/admin/settings?saved=1", status_code=303)
