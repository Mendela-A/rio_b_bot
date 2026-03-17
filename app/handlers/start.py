import asyncio

import asyncpg
from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message

from app import texts
from app.keyboards.main_menu import main_menu_kb
from app.keyboards.admin_kb import admin_kb
from app.handlers.admin import is_admin
from app.database.queries import upsert_user, get_menu_message_id, set_menu_message_id

router = Router()


async def _delete_after(message, delay: float = 5.0) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, pool: asyncpg.Pool) -> None:
    await upsert_user(pool, message.from_user.id, message.from_user.first_name, message.from_user.username)
    old_msg_id = await get_menu_message_id(pool, message.from_user.id)
    if old_msg_id:
        try:
            await bot.delete_message(message.chat.id, old_msg_id)
        except Exception:
            pass
    asyncio.create_task(_delete_after(message, 5.0))
    if await is_admin(bot, message.from_user.id):
        await message.answer("👋 Вітаємо, адміне!", reply_markup=admin_kb())
    sent = await message.answer(texts.get("menu.greeting"), reply_markup=main_menu_kb())
    await set_menu_message_id(pool, message.from_user.id, sent.message_id)
