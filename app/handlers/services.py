import asyncpg
from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.database.queries import get_services_by_type, get_service_by_id, get_child_services
from app.keyboards.services_kb import services_kb, subcategories_kb, service_detail_kb

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

    text = f"{label}\n\nОберіть послугу:" if services else f"{label}\n\nПослуги тимчасово недоступні."

    await callback.message.edit_text(text, reply_markup=services_kb(services, category_type))
    await callback.answer()


@router.callback_query(F.data.startswith("service:"))
async def show_service_detail(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    parts = callback.data.split(":")
    category_type = parts[1]
    service_id = int(parts[2])

    service = await get_service_by_id(pool, service_id)
    children = await get_child_services(pool, service_id)

    if children:
        await callback.message.edit_text(
            f"<b>{service['name']}</b>\n\nОберіть варіант:",
            reply_markup=subcategories_kb(children, category_type),
        )
    else:
        price_line = f"\n💰 Ціна: {service['price']:.0f} грн" if service['price'] else ""
        description = f"\n📝 {service['description']}" if service['description'] else ""
        text = f"<b>{service['name']}</b>{price_line}{description}"
        await callback.message.edit_text(text, reply_markup=service_detail_kb(category_type))

    await callback.answer()
