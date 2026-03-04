import asyncpg
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def _service_label(s: asyncpg.Record) -> str:
    return f"{s['name']} — {s['price']:.0f} грн" if s['price'] else s['name']


def services_kb(services: list[asyncpg.Record], category_type: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=_service_label(s),
            callback_data=f"service:{category_type}:{s['id']}",
        )]
        for s in services
    ]
    buttons.append([
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subcategories_kb(services: list[asyncpg.Record], category_type: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=_service_label(s),
            callback_data=f"service:{category_type}:{s['id']}",
        )]
        for s in services
    ]
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"services:{category_type}"),
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_detail_kb(category_type: str, service_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Замовити", callback_data=f"quick:start:{service_id}")],
        [InlineKeyboardButton(text="➕ Додати до кошику", callback_data=f"cart:add:{category_type}:{service_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"services:{category_type}"),
            InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
        ],
    ])
