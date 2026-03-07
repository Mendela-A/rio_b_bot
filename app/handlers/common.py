from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from app.keyboards.main_menu import main_menu_kb
from app.handlers._utils import edit_or_replace

router = Router()

WELCOME_TEXT = (
    "Вітаємо у дитячому розважальному центрі «РІО» 💛\n"
    "Раді бачити вас! Оберіть, будь ласка, що вас цікавить:"
)


@router.callback_query(F.data == "main_menu")
async def go_main_menu(callback: CallbackQuery) -> None:
    await edit_or_replace(callback, WELCOME_TEXT, reply_markup=main_menu_kb())
    await callback.answer()


@router.message()
async def ignore_text(message: Message) -> None:
    pass
