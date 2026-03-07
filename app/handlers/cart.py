import asyncpg
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app import texts
from app.database.queries import cart_add, cart_get, cart_remove, get_services_by_type
from app.keyboards.booking_kb import cart_kb
from app.keyboards.services_kb import services_kb

router = Router()

_CATEGORY_LABELS = {
    "venue": "🎉 Додаткові послуги",
    "offsite": "🤹 Аніматор на виїзд",
    "program": "🎭 Програми та аніматори",
}


def _empty_cart_kb(in_booking: bool) -> InlineKeyboardMarkup:
    if in_booking:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад до підтвердження", callback_data="booking:resume_confirm")],
            [InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Забронювати без послуг", callback_data="booking:start")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")],
    ])


def _cart_text(cart_items: list[asyncpg.Record]) -> str:
    lines = ["🛒 <b>Ваш кошик:</b>\n"]
    total = 0
    for item in cart_items:
        price = item["price"]
        qty = item["quantity"]
        if price:
            subtotal = price * qty
            total += subtotal
            lines.append(f"• {item['name']} — {price:.0f} грн × {qty} = {subtotal:.0f} грн")
        else:
            lines.append(f"• {item['name']} × {qty}")
    if total:
        lines.append(f"\n💰 Разом: {total:.0f} грн")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("cart:add:"))
async def cart_add_handler(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    parts = callback.data.split(":")          # cart : add : category_type : service_id
    category_type = parts[2]
    service_id = int(parts[3])

    await cart_add(pool, callback.from_user.id, service_id)
    await callback.answer(texts.get("cart.added"))

    # Auto-return to services list
    items = await get_services_by_type(pool, category_type)
    label = _CATEGORY_LABELS.get(category_type, "Послуги")
    text = f"{label}\n\nОберіть послугу:" if items else f"{label}\n\nПослуги тимчасово недоступні."
    from app.handlers._utils import edit_or_replace
    await edit_or_replace(callback, text, reply_markup=services_kb(items, category_type))


@router.callback_query(F.data == "cart:view")
async def cart_view_handler(callback: CallbackQuery, pool: asyncpg.Pool, state: FSMContext) -> None:
    in_booking = (await state.get_state()) is not None
    items = await cart_get(pool, callback.from_user.id)
    if not items:
        await callback.message.edit_text(texts.get("cart.empty"), reply_markup=_empty_cart_kb(in_booking))
    else:
        await callback.message.edit_text(_cart_text(items), reply_markup=cart_kb(items, in_booking))
    await callback.answer()


@router.callback_query(F.data.startswith("cart:remove:"))
async def cart_remove_handler(callback: CallbackQuery, pool: asyncpg.Pool, state: FSMContext) -> None:
    service_id = int(callback.data.split(":")[2])
    await cart_remove(pool, callback.from_user.id, service_id)

    in_booking = (await state.get_state()) is not None
    items = await cart_get(pool, callback.from_user.id)
    if not items:
        await callback.message.edit_text(texts.get("cart.empty"), reply_markup=_empty_cart_kb(in_booking))
    else:
        await callback.message.edit_text(_cart_text(items), reply_markup=cart_kb(items, in_booking))
    await callback.answer("🗑️ Видалено")
