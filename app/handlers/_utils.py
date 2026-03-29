import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def delete_after(bot: Bot, chat_id: int, message_id: int, delay: float = 10.0) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def edit_or_replace(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    """Edit message text, or delete+send if current message cannot be edited (e.g. photo)."""
    try:
        return await callback.message.edit_text(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )
    except TelegramBadRequest:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        return await callback.message.answer(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )
