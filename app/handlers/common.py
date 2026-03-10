from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from app import texts
from app.keyboards.main_menu import main_menu_kb
from app.handlers._utils import edit_or_replace
from app.database.queries import get_menu_message_id, set_menu_message_id
import asyncpg

router = Router()


@router.callback_query(F.data == "main_menu")
async def go_main_menu(callback: CallbackQuery, bot: Bot, pool: asyncpg.Pool) -> None:
    old_msg_id = await get_menu_message_id(pool, callback.from_user.id)
    if old_msg_id and old_msg_id != callback.message.message_id:
        # Натиснуто з не-меню повідомлення (розсилка тощо) — лишити його, видалити старе меню
        try:
            await bot.delete_message(callback.message.chat.id, old_msg_id)
        except Exception:
            pass
        sent = await callback.message.answer(
            texts.get("menu.greeting"), reply_markup=main_menu_kb()
        )
    else:
        # Натиснуто з самого меню — редагувати in-place
        sent = await edit_or_replace(callback, texts.get("menu.greeting"), reply_markup=main_menu_kb())
    await set_menu_message_id(pool, callback.from_user.id, sent.message_id)
    await callback.answer()


@router.message()
async def ignore_text(message: Message) -> None:
    pass
