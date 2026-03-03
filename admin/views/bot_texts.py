import os

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)

# key → (default_value, hint_for_operator)
_REGISTRY: dict[str, tuple[str, str]] = {
    "menu.greeting": (
        "Вітаємо у дитячому розважальному центрі «РІО» 💛\n"
        "Раді бачити вас! Оберіть, будь ласка, що вас цікавить:",
        "Привітання при /start",
    ),
    "booking.ask_name": (
        "📝 Введіть прізвище та ім'я:",
        "Запит імені (крок 1)",
    ),
    "booking.ask_phone": (
        "📱 Введіть номер телефону або натисніть кнопку нижче:",
        "Запит телефону (крок 2)",
    ),
    "booking.ask_children": (
        "👶 Скільки дітей буде на святі?",
        "Запит кількості дітей (крок 3)",
    ),
    "booking.ask_date": (
        "📅 Оберіть дату:",
        "Запит дати (крок 4)",
    ),
    "booking.success": (
        "✅ Бронювання #{id} прийнято!\n\nМи зв'яжемося з вами для підтвердження.",
        "Підтвердження бронювання  —  {id} буде замінено на номер",
    ),
    "booking.cancelled": (
        "Бронювання скасовано.",
        "Повідомлення про скасування",
    ),
    "cart.added": (
        "✅ Додано до кошика!",
        "Спливаюче повідомлення при додаванні послуги",
    ),
    "cart.empty": (
        "🛒 Кошик порожній.",
        "Повідомлення про порожній кошик",
    ),
}


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
            rows = await conn.fetch("SELECT key, value FROM bot_texts")
        db_values = {r["key"]: r["value"] for r in rows}

        items = [
            {
                "key": key,
                "hint": hint,
                "value": db_values.get(key, default),
                "is_custom": key in db_values,
            }
            for key, (default, hint) in _REGISTRY.items()
        ]

        return _templates.TemplateResponse(
            "bot_texts.html",
            {"request": request, "items": items},
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
                    await conn.execute("DELETE FROM bot_texts WHERE key=$1", key)
                elif value:
                    await conn.execute(
                        """
                        INSERT INTO bot_texts (key, value) VALUES ($1, $2)
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                        """,
                        key, value,
                    )

        return RedirectResponse("/admin/bot-texts", status_code=303)
