from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Бронювання", callback_data="booking")],
        [InlineKeyboardButton(text="🎉 Додаткові послуги", callback_data="services:venue")],
        [InlineKeyboardButton(text="🤹 Аніматор на виїзд", callback_data="services:offsite")],
        [InlineKeyboardButton(text="🎭 Програми та аніматори", callback_data="services:program")],
        [InlineKeyboardButton(text="ℹ️ Інформація про заклад", callback_data="info:list")],
    ])
