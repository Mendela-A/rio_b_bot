import asyncpg
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def services_kb(services: list[asyncpg.Record], category_type: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"{s['name']} — {s['price']:.0f} грн",
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
            text=f"{s['name']} — {s['price']:.0f} грн",
            callback_data=f"service:{category_type}:{s['id']}",
        )]
        for s in services
    ]
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"services:{category_type}"),
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_detail_kb(category_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати до кошику", callback_data="cart:coming_soon")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"services:{category_type}"),
            InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
        ],
    ])
