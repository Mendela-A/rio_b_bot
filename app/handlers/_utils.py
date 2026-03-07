from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def edit_or_replace(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    """Edit message text, or delete+send if current message is a photo."""
    if callback.message.photo:
        await callback.message.delete()
        return await callback.message.answer(text, reply_markup=reply_markup)
    else:
        return await callback.message.edit_text(text, reply_markup=reply_markup)
