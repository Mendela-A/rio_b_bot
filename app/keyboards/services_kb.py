import asyncpg
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def _service_label(s: asyncpg.Record) -> str:
    return f"{s['name']} — {s['price']:.0f} грн" if s['price'] else s['name']


def services_kb(services: list[asyncpg.Record], category_type: str, from_booking: bool = False) -> InlineKeyboardMarkup:
    prefix = "service_b" if from_booking else "service"
    buttons = [
        [InlineKeyboardButton(
            text=_service_label(s),
            callback_data=f"{prefix}:{category_type}:{s['id']}",
        )]
        for s in services
    ]
    if from_booking:
        buttons.append([InlineKeyboardButton(text="↩️ До підтвердження", callback_data="booking:resume_confirm")])
    else:
        buttons.append([InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subcategories_kb(services: list[asyncpg.Record], category_type: str, from_booking: bool = False) -> InlineKeyboardMarkup:
    prefix = "service_b" if from_booking else "service"
    back_cb = f"services_b:{category_type}" if from_booking else f"services:{category_type}"
    buttons = [
        [InlineKeyboardButton(
            text=_service_label(s),
            callback_data=f"{prefix}:{category_type}:{s['id']}",
        )]
        for s in services
    ]
    if from_booking:
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb),
            InlineKeyboardButton(text="↩️ До підтвердження", callback_data="booking:resume_confirm"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb),
            InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_detail_kb(category_type: str, service_id: int, from_booking: bool = False) -> InlineKeyboardMarkup:
    add_cb = f"cart:add_b:{category_type}:{service_id}" if from_booking else f"cart:add:{category_type}:{service_id}"
    back_cb = f"services_b:{category_type}" if from_booking else f"services:{category_type}"
    if from_booking:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати до кошику", callback_data=add_cb)],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb),
                InlineKeyboardButton(text="↩️ До підтвердження", callback_data="booking:resume_confirm"),
            ],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Замовити", callback_data=f"quick:start:{service_id}")],
        [InlineKeyboardButton(text="➕ Додати до кошику", callback_data=add_cb)],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb),
            InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
        ],
    ])
