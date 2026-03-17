import asyncpg
from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.database.queries import get_info_pages, get_info_page_by_id
from app.keyboards.info_kb import info_list_kb, info_page_kb

router = Router()


@router.callback_query(F.data == "info:list")
async def show_info_list(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    pages = await get_info_pages(pool)
    await callback.message.edit_text(
        "ℹ️ Інформація про заклад\n\nОберіть розділ:",
        reply_markup=info_list_kb(pages),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("info:page:"))
async def show_info_page(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    page_id = int(callback.data.split(":")[2])
    page = await get_info_page_by_id(pool, page_id)
    if not page:
        await callback.answer("Розділ не знайдено", show_alert=True)
        return
    await callback.message.edit_text(
        f"<b>{page['title']}</b>\n\n{page['content']}",
        reply_markup=info_page_kb(),
    )
    await callback.answer()
