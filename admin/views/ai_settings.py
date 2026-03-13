from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db
from shared import templates as _templates

_AI_SETTINGS_KEYS = [
    "ai_enabled",
    "ai_model",
    "ai_company_description",
    "ai_welcome_message",
    "ai_system_prompt",
    "ai_max_tokens",
    "ai_history_limit",
    "ai_no_answer_phrase",
]

_AI_MODELS = [
    ("claude-3-5-haiku-20241022",  "Haiku 3.5  — швидкий, дешевий"),
    ("claude-haiku-4-5-20251001",  "Haiku 4.5  — новіший"),
    ("claude-3-5-sonnet-20241022", "Sonnet 3.5 — розумніший, дорожчий"),
]


class AiSettingsView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Налаштування ШІ",
            icon="fa fa-sliders",
            path="/ai-settings",
            methods=["GET", "POST"],
            name="ai_settings",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value FROM settings WHERE key = ANY($1::text[])",
                _AI_SETTINGS_KEYS,
            )
        values = {r["key"]: r["value"] for r in rows}
        return _templates.TemplateResponse(
            "ai_settings.html",
            {
                "request": request,
                "values": values,
                "models": _AI_MODELS,
                "saved": request.query_params.get("saved"),
            },
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        async with db.pool.acquire() as conn:
            # Checkbox: present = true, absent = false
            ai_enabled = "true" if form.get("ai_enabled") else "false"
            await conn.execute(
                "INSERT INTO settings (key, value) VALUES ('ai_enabled', $1) "
                "ON CONFLICT (key) DO UPDATE SET value = $1",
                ai_enabled,
            )

            model_val = (form.get("ai_model") or "").strip()
            if model_val:
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('ai_model', $1) "
                    "ON CONFLICT (key) DO UPDATE SET value = $1",
                    model_val,
                )

            for key in ("ai_company_description", "ai_welcome_message", "ai_system_prompt", "ai_no_answer_phrase"):
                val = (form.get(key) or "").strip()
                if val:
                    await conn.execute(
                        "INSERT INTO settings (key, value) VALUES ($1, $2) "
                        "ON CONFLICT (key) DO UPDATE SET value = $2",
                        key, val,
                    )

            max_tokens = (form.get("ai_max_tokens") or "").strip()
            if max_tokens.isdigit():
                val = max(256, min(4096, int(max_tokens)))
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('ai_max_tokens', $1) "
                    "ON CONFLICT (key) DO UPDATE SET value = $1",
                    str(val),
                )

            history_limit = (form.get("ai_history_limit") or "").strip()
            if history_limit.isdigit():
                val = max(2, min(50, int(history_limit)))
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('ai_history_limit', $1) "
                    "ON CONFLICT (key) DO UPDATE SET value = $1",
                    str(val),
                )

        return RedirectResponse("/admin/ai-settings?saved=1", status_code=303)
