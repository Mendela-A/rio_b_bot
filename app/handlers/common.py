from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from app.keyboards.main_menu import main_menu_kb

router = Router()

WELCOME_TEXT = (
    "Вітаємо у дитячому розважальному центрі «РІО» 💛\n"
    "Раді бачити вас! Оберіть, будь ласка, що вас цікавить:"
)


@router.callback_query(F.data == "main_menu")
async def go_main_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb())
    await callback.answer()


@router.message()
async def ignore_text(message: Message) -> None:
    pass
