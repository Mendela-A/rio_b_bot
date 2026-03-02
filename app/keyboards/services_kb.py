import asyncpg
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def services_kb(services: list[asyncpg.Record]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"{s['name']} — {s['price']:.0f} грн",
            callback_data=f"service:{s['id']}",
        )]
        for s in services
    ]
    buttons.append([
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
