import asyncpg
from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.database.queries import get_services_by_type
from app.keyboards.services_kb import services_kb

router = Router()

CATEGORY_LABELS = {
    "venue": "🎉 Додаткові послуги",
    "offsite": "🤹 Аніматор на виїзд",
    "program": "🎭 Програми та аніматори",
}


@router.callback_query(F.data.startswith("services:"))
async def show_services(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    category_type = callback.data.split(":")[1]
    services = await get_services_by_type(pool, category_type)
    label = CATEGORY_LABELS.get(category_type, "Послуги")

    if not services:
        text = f"{label}\n\nПослуги тимчасово недоступні."
    else:
        text = f"{label}\n\nОберіть послугу:"

    await callback.message.edit_text(text, reply_markup=services_kb(services))
    await callback.answer()
