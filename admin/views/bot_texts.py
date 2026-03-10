from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db
from shared import templates as _templates


class BotTextsView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Тексти бота",
            icon="fa fa-comment-dots",
            path="/bot-texts",
            methods=["GET", "POST"],
            name="bot_texts",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    # ------------------------------------------------------------------ #
    # GET                                                                  #
    # ------------------------------------------------------------------ #

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, hint, default_value, value FROM bot_texts ORDER BY key"
            )

        GROUP_LABELS = {
            "menu":    "Головне меню",
            "welcome": "Вітання",
            "booking": "Бронювання",
            "cart":    "Кошик",
            "info":    "Інформація",
        }

        groups: dict[str, list] = {}
        for r in rows:
            prefix = r["key"].split(".")[0]
            label = GROUP_LABELS.get(prefix, prefix)
            groups.setdefault(label, []).append({
                "key": r["key"],
                "hint": r["hint"],
                "value": r["value"] if r["value"] is not None else r["default_value"],
                "is_custom": r["value"] is not None,
            })

        return _templates.TemplateResponse(
            "bot_texts.html",
            {"request": request, "groups": groups},
        )

    # ------------------------------------------------------------------ #
    # POST                                                                 #
    # ------------------------------------------------------------------ #

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        key = form.get("key", "").strip()
        value = form.get("value", "").strip()
        action = form.get("_action", "save")

        if key:
            async with db.pool.acquire() as conn:
                if action == "reset":
                    # Keep the row (preserves hint + default_value), just clear override
                    await conn.execute(
                        "UPDATE bot_texts SET value = NULL WHERE key = $1", key
                    )
                elif value:
                    await conn.execute(
                        """
                        INSERT INTO bot_texts (key, value) VALUES ($1, $2)
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                        """,
                        key, value,
                    )

        return RedirectResponse("/admin/bot-texts", status_code=303)
