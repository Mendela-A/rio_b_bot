import calendar
from datetime import date, timedelta

import asyncpg
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

MONTHS_UK = ["січ", "лют", "бер", "кві", "тра", "чер", "лип", "сер", "вер", "жов", "лис", "гру"]
MONTHS_UK_FULL = [
    "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
    "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень",
]


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="booking:cancel")],
    ])


def date_selection_kb(
    days: int = 14,
    blocked: set | None = None,
    blocked_weekdays: set | None = None,
    prefix: str = "booking",
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
        row.append(InlineKeyboardButton(text=label, callback_data=f"{prefix}:date:{d.isoformat()}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📅 Інша дата", callback_data=f"{prefix}:cal:{today.year}:{today.month}")])
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data=f"{prefix}:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def calendar_kb(
    year: int,
    month: int,
    blocked: set | None = None,
    blocked_weekdays: set | None = None,
    prefix: str = "booking",
) -> InlineKeyboardMarkup:
    blocked = blocked or set()
    blocked_weekdays = blocked_weekdays or set()
    today = date.today()
    max_year = today.year + (today.month + 5) // 12
    max_month = (today.month + 5) % 12 or 12

    noop_btn = lambda t: InlineKeyboardButton(text=t, callback_data=f"{prefix}:noop")

    # Navigation row
    is_current = (year == today.year and month == today.month)
    is_max = (year == max_year and month == max_month)

    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month % 12 + 1
    next_year = year + 1 if month == 12 else year

    nav = [
        noop_btn("◀️") if is_current else InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:cal:{prev_year}:{prev_month}"),
        noop_btn(f"{MONTHS_UK_FULL[month - 1]} {year}"),
        noop_btn("▶️") if is_max else InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:cal:{next_year}:{next_month}"),
    ]
    buttons = [nav]

    # Day-of-week header
    buttons.append([noop_btn(d) for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]])

    # Calendar grid
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(noop_btn(" "))
            else:
                d = date(year, month, day)
                if d < today or d in blocked or d.weekday() in blocked_weekdays:
                    row.append(noop_btn(str(day)))
                else:
                    row.append(InlineKeyboardButton(text=str(day), callback_data=f"{prefix}:caldate:{d.isoformat()}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data=f"{prefix}:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cart_kb(
    cart_items: list[asyncpg.Record],
    in_booking: bool = False,
    in_change: bool = False,
) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"🗑️ {item['name']}",
            callback_data=f"cart:remove:{item['service_id']}",
        )]
        for item in cart_items
    ]
    if in_change:
        buttons.append([InlineKeyboardButton(text="↩️ Назад до змін", callback_data="change:resume_confirm")])
    elif in_booking:
        buttons.append([InlineKeyboardButton(text="↩️ Назад до підтвердження", callback_data="booking:resume_confirm")])
    else:
        buttons.append([InlineKeyboardButton(text="📅 Оформити бронювання", callback_data="booking:start")])
    buttons.append([InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_change_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Надіслати запит", callback_data="change:confirm"),
            InlineKeyboardButton(text="🛒 Змінити послуги", callback_data="cart:view"),
        ],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="change:cancel")],
    ])


def confirm_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтвердити", callback_data="booking:confirm")],
        [InlineKeyboardButton(text="🛒 Змінити кошик", callback_data="booking:view_cart")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="booking:cancel")],
    ])
