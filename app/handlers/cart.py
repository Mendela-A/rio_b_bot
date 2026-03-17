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


def _empty_cart_kb(in_booking: bool, in_change: bool = False) -> InlineKeyboardMarkup:
    if in_change:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад до змін", callback_data="change:resume_confirm")],
            [InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")],
        ])
    if in_booking:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати послугу", callback_data="booking:add_service")],
            [InlineKeyboardButton(text="↩️ Назад до підтвердження", callback_data="booking:resume_confirm")],
            [InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎉 Переглянути послуги", callback_data="services:venue")],
        [InlineKeyboardButton(text="🎭 Програми та аніматори", callback_data="services:program")],
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


@router.callback_query(F.data.startswith("cart:add_b:"))
async def cart_add_booking_handler(callback: CallbackQuery, pool: asyncpg.Pool, state: FSMContext) -> None:
    parts = callback.data.split(":")          # cart : add_b : category_type : service_id
    service_id = int(parts[3])
    await cart_add(pool, callback.from_user.id, service_id)
    await callback.answer(texts.get("cart.added"))

    from app.handlers._utils import edit_or_replace
    from app.keyboards.booking_kb import confirm_booking_kb
    from app.keyboards.main_menu import main_menu_kb
    from app.handlers.booking import _confirmation_text
    data = await state.get_data()
    if not data.get("full_name"):
        await edit_or_replace(callback, "Сесія застаріла. Почніть бронювання знову.", reply_markup=main_menu_kb())
        await state.clear()
        return
    cart_items = await cart_get(pool, callback.from_user.id)
    await edit_or_replace(callback, _confirmation_text(data, cart_items), reply_markup=confirm_booking_kb())


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


def _state_flags(current_state: str | None) -> tuple[bool, bool]:
    """Returns (in_booking, in_change) based on FSM state string."""
    if current_state is None:
        return False, False
    in_change = "ChangeStates" in current_state
    in_booking = not in_change and current_state is not None
    return in_booking, in_change


@router.callback_query(F.data == "cart:view")
async def cart_view_handler(callback: CallbackQuery, pool: asyncpg.Pool, state: FSMContext) -> None:
    in_booking, in_change = _state_flags(await state.get_state())
    items = await cart_get(pool, callback.from_user.id)
    if not items:
        await callback.message.edit_text(texts.get("cart.empty"), reply_markup=_empty_cart_kb(in_booking, in_change))
    else:
        await callback.message.edit_text(_cart_text(items), reply_markup=cart_kb(items, in_booking, in_change))
    await callback.answer()


@router.callback_query(F.data.startswith("cart:remove:"))
async def cart_remove_handler(callback: CallbackQuery, pool: asyncpg.Pool, state: FSMContext) -> None:
    service_id = int(callback.data.split(":")[2])
    await cart_remove(pool, callback.from_user.id, service_id)

    in_booking, in_change = _state_flags(await state.get_state())
    items = await cart_get(pool, callback.from_user.id)
    if not items:
        await callback.message.edit_text(texts.get("cart.empty"), reply_markup=_empty_cart_kb(in_booking, in_change))
    else:
        await callback.message.edit_text(_cart_text(items), reply_markup=cart_kb(items, in_booking, in_change))
    await callback.answer("🗑️ Видалено")
