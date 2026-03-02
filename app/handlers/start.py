from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from app.keyboards.main_menu import main_menu_kb

router = Router()

WELCOME_TEXT = (
    "Вітаємо у дитячому розважальному центрі «РІО» 💛\n"
    "Раді бачити вас! Оберіть, будь ласка, що вас цікавить:"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())
