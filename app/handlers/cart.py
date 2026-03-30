import asyncpg
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from app import texts
from app.database.queries import (
    cart_add, cart_get, cart_remove, get_services_by_type,
    get_entry_tariff, get_service_by_id,
)
from app.keyboards.booking_kb import cart_kb, confirm_booking_kb
from app.keyboards.main_menu import main_menu_kb
from app.keyboards.services_kb import services_kb
from app.handlers._utils import edit_or_replace, confirmation_text
from app.handlers.booking import BookingStates

router = Router()

_CATEGORY_LABELS = {
    "venue": "🎉 Додаткові послуги",
    "offsite": "🤹 Аніматор на виїзд",
    "program": "🎭 Програми та аніматори",
}


class CartStates(StatesGroup):
    waiting_service_quantity = State()


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
        qty = item["quantity"]
        ppc = item.get("price_per_child")
        price = item["price"]
        if ppc:
            subtotal = ppc * qty
            total += subtotal
            lines.append(f"• {item['name']} — {ppc:.0f} грн/дитина × {qty} = {subtotal:.0f} грн")
        elif price:
            subtotal = price * qty
            total += subtotal
            lines.append(f"• {item['name']} — {price:.0f} грн × {qty} = {subtotal:.0f} грн")
        else:
            lines.append(f"• {item['name']} × {qty}")
    if total:
        lines.append(f"\n💰 Разом: {total:.0f} грн")
    return "\n".join(lines)


async def _ask_children_count(callback: CallbackQuery, state: FSMContext,
                               service_id: int, service_name: str,
                               category_type: str, in_booking: bool) -> None:
    await state.update_data(
        pending_service_id=service_id,
        pending_category=category_type,
        pending_in_booking=in_booking,
    )
    await state.set_state(CartStates.waiting_service_quantity)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cart:cancel_qty")]
    ])
    await callback.message.edit_text(
        f"👶 Для скількох дітей додати «{service_name}»?\n\nВведіть кількість:",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cart:add_b:"))
async def cart_add_booking_handler(callback: CallbackQuery, pool: asyncpg.Pool, state: FSMContext) -> None:
    parts = callback.data.split(":")          # cart : add_b : category_type : service_id
    category_type = parts[2]
    service_id = int(parts[3])

    service = await get_service_by_id(pool, service_id)
    if service and service["price_per_child"]:
        await _ask_children_count(callback, state, service_id, service["name"], category_type, in_booking=True)
        return

    await cart_add(pool, callback.from_user.id, service_id)
    await callback.answer(texts.get("cart.added"))

    data = await state.get_data()
    if not data.get("full_name"):
        await edit_or_replace(callback, "Сесія застаріла. Почніть бронювання знову.", reply_markup=main_menu_kb())
        await state.clear()
        return
    cart_items = await cart_get(pool, callback.from_user.id)
    entry_rate = await get_entry_tariff(pool, data["booking_date"])
    await edit_or_replace(callback, confirmation_text(data, cart_items, entry_rate), reply_markup=confirm_booking_kb())


@router.callback_query(F.data.startswith("cart:add:"))
async def cart_add_handler(callback: CallbackQuery, pool: asyncpg.Pool, state: FSMContext) -> None:
    parts = callback.data.split(":")          # cart : add : category_type : service_id
    category_type = parts[2]
    service_id = int(parts[3])

    service = await get_service_by_id(pool, service_id)
    if service and service["price_per_child"]:
        await _ask_children_count(callback, state, service_id, service["name"], category_type, in_booking=False)
        return

    await cart_add(pool, callback.from_user.id, service_id)
    await callback.answer(texts.get("cart.added"))

    items = await get_services_by_type(pool, category_type)
    label = _CATEGORY_LABELS.get(category_type, "Послуги")
    text = f"{label}\n\nОберіть послугу:" if items else f"{label}\n\nПослуги тимчасово недоступні."
    await edit_or_replace(callback, text, reply_markup=services_kb(items, category_type))


@router.callback_query(F.data == "cart:cancel_qty", CartStates.waiting_service_quantity)
async def cart_cancel_qty(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    data = await state.get_data()
    in_booking = data.get("pending_in_booking", False)
    category_type = data.get("pending_category", "venue")

    await state.set_data({k: v for k, v in data.items()
                          if k not in ("pending_service_id", "pending_category", "pending_in_booking")})

    if in_booking:
        await state.set_state(None)
        fresh_data = await state.get_data()
        cart_items = await cart_get(pool, callback.from_user.id)
        entry_rate = await get_entry_tariff(pool, fresh_data.get("booking_date", ""))
        await edit_or_replace(callback, confirmation_text(fresh_data, cart_items, entry_rate),
                              reply_markup=confirm_booking_kb())
    else:
        await state.set_state(None)
        items = await get_services_by_type(pool, category_type)
        label = _CATEGORY_LABELS.get(category_type, "Послуги")
        text = f"{label}\n\nОберіть послугу:" if items else f"{label}\n\nПослуги тимчасово недоступні."
        await edit_or_replace(callback, text, reply_markup=services_kb(items, category_type))
    await callback.answer()


@router.message(CartStates.waiting_service_quantity)
async def cart_service_quantity_handler(message: Message, pool: asyncpg.Pool, state: FSMContext) -> None:
    text = (message.text or "").strip()
    try:
        count = int(text)
        if count < 1 or count > 50:
            raise ValueError
    except ValueError:
        await message.answer("Введіть ціле число від 1 до 50.")
        return

    data = await state.get_data()
    service_id = data["pending_service_id"]
    category_type = data.get("pending_category", "venue")
    in_booking = data.get("pending_in_booking", False)

    await cart_add(pool, message.from_user.id, service_id, quantity=count)

    # Clear pending keys, restore booking state if needed
    new_data = {k: v for k, v in data.items()
                if k not in ("pending_service_id", "pending_category", "pending_in_booking")}
    await state.set_data(new_data)

    if in_booking:
        await state.set_state(BookingStates.waiting_date)
        cart_items = await cart_get(pool, message.from_user.id)
        entry_rate = await get_entry_tariff(pool, new_data.get("booking_date", ""))
        await message.answer(
            confirmation_text(new_data, cart_items, entry_rate),
            reply_markup=confirm_booking_kb(),
        )
    else:
        await state.set_state(None)
        items = await get_services_by_type(pool, category_type)
        label = _CATEGORY_LABELS.get(category_type, "Послуги")
        await message.answer(
            f"✅ Додано до кошика!\n\n{label}\n\nОберіть послугу:",
            reply_markup=services_kb(items, category_type),
        )


def _state_flags(current_state: str | None) -> tuple[bool, bool]:
    """Returns (in_booking, in_change) based on FSM state string."""
    if current_state is None:
        return False, False
    in_change = "ChangeStates" in current_state
    in_booking = "BookingStates" in current_state
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
