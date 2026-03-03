import asyncpg
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def info_list_kb(pages: list[asyncpg.Record]) -> InlineKeyboardMarkup:
    btns = [InlineKeyboardButton(text=p['title'], callback_data=f"info:page:{p['id']}") for p in pages]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append([InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def info_page_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Назад", callback_data="info:list"),
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"),
    ]])
