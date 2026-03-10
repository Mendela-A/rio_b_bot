import asyncpg
from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message

from app import texts
from app.keyboards.main_menu import main_menu_kb
from app.keyboards.admin_kb import admin_kb
from app.handlers.admin import is_admin
from app.database.queries import upsert_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, pool: asyncpg.Pool) -> None:
    await upsert_user(pool, message.from_user.id, message.from_user.first_name, message.from_user.username)
    if await is_admin(bot, message.from_user.id):
        await message.answer(
            "👋 Вітаємо, адміне!",
            reply_markup=admin_kb(),
        )
    await message.answer(texts.get("menu.greeting"), reply_markup=main_menu_kb())
