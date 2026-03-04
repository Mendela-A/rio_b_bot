from datetime import date, timedelta

import asyncpg
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

MONTHS_UK = ["січ", "лют", "бер", "кві", "тра", "чер", "лип", "сер", "вер", "жов", "лис", "гру"]


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="booking:cancel")],
    ])


def date_selection_kb(
    days: int = 14,
    blocked: set | None = None,
    blocked_weekdays: set | None = None,
) -> InlineKeyboardMarkup:
    blocked = blocked or set()
    blocked_weekdays = blocked_weekdays or set()
    today = date.today()
    buttons = []
    row = []
    for i in range(1, days + 1):
        d = today + timedelta(days=i)
        if d in blocked or d.weekday() in blocked_weekdays:
            continue
        label = f"{d.day} {MONTHS_UK[d.month - 1]}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"booking:date:{d.isoformat()}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="booking:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cart_kb(cart_items: list[asyncpg.Record], in_booking: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"🗑️ {item['name']}",
            callback_data=f"cart:remove:{item['service_id']}",
        )]
        for item in cart_items
    ]
    if in_booking:
        buttons.append([InlineKeyboardButton(text="↩️ Назад до підтвердження", callback_data="booking:resume_confirm")])
    else:
        buttons.append([InlineKeyboardButton(text="📅 Оформити бронювання", callback_data="booking:start")])
    buttons.append([InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтвердити", callback_data="booking:confirm")],
        [InlineKeyboardButton(text="🛒 Змінити кошик", callback_data="booking:view_cart")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="booking:cancel")],
    ])
