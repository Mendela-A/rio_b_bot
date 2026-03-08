from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def admin_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🔵 Непідтверджені")],
            [KeyboardButton(text="📅 Бронювання сьогодні"), KeyboardButton(text="📅 Тиждень")],
            [KeyboardButton(text="📢 Розсилка"), KeyboardButton(text="⚙ Налаштування")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
