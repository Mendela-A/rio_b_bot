from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db
from shared import templates as _templates


class TariffEditorView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Тарифи",
            icon="fa fa-ticket",
            path="/tariff-editor",
            methods=["GET", "POST"],
            name="tariff_editor",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value FROM settings WHERE key IN ('tariff_weekday', 'tariff_weekend')"
            )
        tariffs = {r["key"]: r["value"] for r in rows}
        return _templates.TemplateResponse(
            "tariff_editor.html",
            {
                "request": request,
                "tariff_weekday": tariffs.get("tariff_weekday", "0"),
                "tariff_weekend": tariffs.get("tariff_weekend", "0"),
                "saved": request.query_params.get("saved"),
            },
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        weekday = _float_or_zero(form.get("tariff_weekday"))
        weekend = _float_or_zero(form.get("tariff_weekend"))
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE settings SET value=$1 WHERE key='tariff_weekday'", str(weekday)
            )
            await conn.execute(
                "UPDATE settings SET value=$1 WHERE key='tariff_weekend'", str(weekend)
            )
        return RedirectResponse("/admin/tariff-editor?saved=1", status_code=303)


def _float_or_zero(value) -> float:
    try:
        v = float(value)
        return max(v, 0)
    except (TypeError, ValueError):
        return 0.0
