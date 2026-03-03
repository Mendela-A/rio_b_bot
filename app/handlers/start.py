from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app import texts
from app.keyboards.main_menu import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(texts.get("menu.greeting"), reply_markup=main_menu_kb())
