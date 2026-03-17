import asyncio
import logging
import re
from datetime import date as dt_date

import asyncpg
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, Message,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from app import texts
from app.config import load_config
from app.database.queries import (
    cart_get, cart_add, cart_clear, create_booking, create_booking_items, get_user_bookings,
    get_service_by_id, create_inquiry, get_setting, get_blocked_dates, get_blocked_weekdays,
    get_booking_by_id, update_booking_status, get_booking_items,
    create_change_request, create_change_items, get_change_request, get_pending_change_for_booking,
    update_change_request_status, apply_change_request,
)
from app.keyboards.booking_kb import (
    cancel_kb, date_selection_kb, calendar_kb, confirm_booking_kb, cart_kb, confirm_change_kb,
    add_service_categories_kb,
)
from app.keyboards.main_menu import main_menu_kb

router = Router()
logger = logging.getLogger(__name__)
_config = load_config()

_MSG_TTL = 10.0  # seconds before validation error messages disappear


class BookingStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_children = State()
    waiting_date = State()
    waiting_cancel_reason = State()
    quick_waiting_name = State()
    quick_waiting_phone = State()


class ChangeStates(StatesGroup):
    waiting_date = State()
    waiting_children = State()
    confirming = State()


def _phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поділитись номером", request_contact=True)],
            [KeyboardButton(text="❌ Скасувати")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _try_delete(bot: Bot, chat_id: int, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def _delete_after(bot: Bot, chat_id: int, message_id: int, delay: float = _MSG_TTL) -> None:
    await asyncio.sleep(delay)
    await _try_delete(bot, chat_id, message_id)


def _cart_text(cart_items: list) -> str:
    lines = ["🛒 <b>Ваш кошик:</b>\n"]
    total = 0
    for item in cart_items:
        price, qty = item["price"], item["quantity"]
        if price:
            subtotal = price * qty
            total += subtotal
            lines.append(f"• {item['name']} — {price:.0f} грн × {qty} = {subtotal:.0f} грн")
        else:
            lines.append(f"• {item['name']} × {qty}")
    if total:
        lines.append(f"\n💰 Разом: {total:.0f} грн")
    return "\n".join(lines)


# --- Start FSM ---

@router.callback_query(F.data == "booking:start")
async def booking_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BookingStates.waiting_name)
    await callback.message.edit_text(texts.get("booking.ask_name"), reply_markup=cancel_kb())
    await state.update_data(bot_msg_id=callback.message.message_id)
    await callback.answer()


# --- Step 1: name ---

@router.message(BookingStates.waiting_name)
async def booking_name(message: Message, state: FSMContext, bot: Bot) -> None:
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
        err = await message.answer("⚠️ Введіть ім'я (мінімум 2 символи)")
        asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
        return

    data = await state.get_data()
    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))

    await state.update_data(full_name=name)
    await state.set_state(BookingStates.waiting_phone)
    sent = await message.answer(
        texts.get("booking.ask_phone"),
        reply_markup=_phone_kb(),
    )
    await state.update_data(bot_msg_id=sent.message_id)


# --- Step 2: phone ---

@router.message(BookingStates.waiting_phone)
async def booking_phone(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()

    # Cancel via reply keyboard
    if message.text == "❌ Скасувати":
        await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
        asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
        await state.clear()
        msg = await message.answer("Бронювання скасовано.", reply_markup=ReplyKeyboardRemove())
        asyncio.create_task(_delete_after(bot, message.chat.id, msg.message_id))
        await message.answer("Головне меню:", reply_markup=main_menu_kb())
        return

    # Contact shared via button
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    elif message.text:
        phone = message.text.strip()
        if not re.match(r'^[\d\s\+\-\(\)]{10,}$', phone):
            asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
            err = await message.answer(
                "⚠️ Невірний формат. Введіть телефон або натисніть кнопку нижче:",
                reply_markup=_phone_kb(),
            )
            asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
            return
    else:
        asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
        return

    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))

    await state.update_data(phone=phone)
    await state.set_state(BookingStates.waiting_children)
    sent = await message.answer(texts.get("booking.ask_children"), reply_markup=cancel_kb())
    await state.update_data(bot_msg_id=sent.message_id)


# --- Step 3: children count ---

@router.message(BookingStates.waiting_children)
async def booking_children(message: Message, state: FSMContext, bot: Bot, pool: asyncpg.Pool) -> None:
    text = message.text.strip() if message.text else ""
    try:
        count = int(text)
        if count <= 0:
            raise ValueError
    except ValueError:
        asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
        err = await message.answer("⚠️ Введіть ціле число більше 0")
        asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
        return

    data = await state.get_data()
    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))

    await state.update_data(children_count=count)
    await state.set_state(BookingStates.waiting_date)
    days = int(await get_setting(pool, "booking_days_ahead", "14"))
    blocked = await get_blocked_dates(pool)
    blocked_weekdays = await get_blocked_weekdays(pool)
    sent = await message.answer(texts.get("booking.ask_date"), reply_markup=date_selection_kb(days, blocked, blocked_weekdays))
    await state.update_data(bot_msg_id=sent.message_id)


# --- Step 4: date selection ---

@router.callback_query(F.data.startswith("booking:date:"), BookingStates.waiting_date)
async def booking_date(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    from datetime import timedelta
    raw = callback.data.split(":", 2)[2]

    try:
        parsed = dt_date.fromisoformat(raw)
    except ValueError:
        await callback.answer("Невірна дата", show_alert=True)
        return

    today = dt_date.today()
    days_ahead = int(await get_setting(pool, "booking_days_ahead", "14"))
    if not (today <= parsed <= today + timedelta(days=days_ahead)):
        await callback.answer("Ця дата недоступна", show_alert=True)
        return

    blocked = await get_blocked_dates(pool)
    blocked_wdays = await get_blocked_weekdays(pool)
    if parsed in blocked or parsed.weekday() in blocked_wdays:
        await callback.answer("Ця дата заблокована", show_alert=True)
        return

    await state.update_data(booking_date=raw)

    data = await state.get_data()
    cart_items = await cart_get(pool, callback.from_user.id)

    await callback.message.edit_text(_confirmation_text(data, cart_items), reply_markup=confirm_booking_kb())
    await state.update_data(bot_msg_id=callback.message.message_id)
    await callback.answer()


# --- Calendar navigation ---

@router.callback_query(F.data.startswith("booking:cal:"), BookingStates.waiting_date)
async def booking_calendar_nav(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    parts = callback.data.split(":")
    year, month = int(parts[2]), int(parts[3])
    blocked = await get_blocked_dates(pool)
    blocked_weekdays = await get_blocked_weekdays(pool)
    await callback.message.edit_reply_markup(reply_markup=calendar_kb(year, month, blocked, blocked_weekdays))
    await callback.answer()


@router.callback_query(F.data.startswith("booking:caldate:"), BookingStates.waiting_date)
async def booking_caldate(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    raw = callback.data.split(":", 2)[2]
    try:
        parsed = dt_date.fromisoformat(raw)
    except ValueError:
        await callback.answer("Невірна дата", show_alert=True)
        return

    today = dt_date.today()
    if parsed < today:
        await callback.answer("Ця дата вже минула", show_alert=True)
        return

    blocked = await get_blocked_dates(pool)
    blocked_wdays = await get_blocked_weekdays(pool)
    if parsed in blocked or parsed.weekday() in blocked_wdays:
        await callback.answer("Ця дата заблокована", show_alert=True)
        return

    await state.update_data(booking_date=raw)
    data = await state.get_data()
    cart_items = await cart_get(pool, callback.from_user.id)
    await callback.message.edit_text(_confirmation_text(data, cart_items), reply_markup=confirm_booking_kb())
    await state.update_data(bot_msg_id=callback.message.message_id)
    await callback.answer()


@router.callback_query(F.data == "booking:noop")
async def booking_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# --- Add service from booking confirmation ---

@router.callback_query(F.data == "booking:add_service")
async def booking_add_service(callback: CallbackQuery) -> None:
    from app.handlers._utils import edit_or_replace
    await edit_or_replace(callback, "Оберіть категорію послуг:", reply_markup=add_service_categories_kb())
    await callback.answer()


# --- View cart from booking confirmation ---

@router.callback_query(F.data == "booking:view_cart")
async def booking_view_cart(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    items = await cart_get(pool, callback.from_user.id)
    if not items:
        await callback.message.edit_text(
            "🛒 Кошик порожній.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Додати послугу", callback_data="booking:add_service")],
                [InlineKeyboardButton(text="↩️ Назад до підтвердження", callback_data="booking:resume_confirm")],
                [InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")],
            ]),
        )
    else:
        await callback.message.edit_text(_cart_text(items), reply_markup=cart_kb(items, in_booking=True))
    await callback.answer()


# --- Resume confirmation after editing cart ---

@router.callback_query(F.data == "booking:resume_confirm")
async def booking_resume_confirm(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    data = await state.get_data()
    if not data.get("full_name"):
        await callback.message.edit_text("Сесія застаріла. Почніть бронювання знову.", reply_markup=main_menu_kb())
        await state.clear()
        await callback.answer()
        return
    cart_items = await cart_get(pool, callback.from_user.id)
    await callback.message.edit_text(_confirmation_text(data, cart_items), reply_markup=confirm_booking_kb())
    await callback.answer()


# --- Confirm ---

@router.callback_query(F.data == "booking:confirm")
async def booking_confirm(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool, bot: Bot) -> None:
    await callback.answer()  # відповідаємо одразу, щоб кнопка не "крутилась"

    data = await state.get_data()
    if not data.get("full_name"):
        await callback.message.edit_text("Сесія застаріла. Почніть бронювання знову.", reply_markup=main_menu_kb())
        await state.clear()
        return

    cart_items = await cart_get(pool, callback.from_user.id)

    try:
        booking_id = await create_booking(
            pool,
            telegram_id=callback.from_user.id,
            full_name=data["full_name"],
            phone=data["phone"],
            children_count=data["children_count"],
            booking_date=dt_date.fromisoformat(data["booking_date"]),
        )
    except Exception as e:
        logger.error("create_booking failed: %s", e)
        await callback.message.edit_text(
            "⚠️ Помилка при збереженні бронювання. Спробуйте ще раз.",
            reply_markup=confirm_booking_kb(),
        )
        return

    try:
        if cart_items:
            await create_booking_items(pool, booking_id, cart_items)
            await cart_clear(pool, callback.from_user.id)
    except Exception as e:
        logger.error("create_booking_items failed: %s", e)

    await state.clear()

    await callback.message.edit_text(
        texts.get("booking.success", id=booking_id),
        reply_markup=main_menu_kb(),
    )

    await _notify_admin(bot, booking_id, data, cart_items)


# --- Cancel ---

@router.callback_query(F.data == "booking:cancel")
async def booking_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.get("booking.cancelled"), reply_markup=main_menu_kb())
    await callback.answer()


# --- Quick booking ---

@router.callback_query(F.data.startswith("quick:start:"))
async def quick_start(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    service_id = int(callback.data.split(":")[2])
    service = await get_service_by_id(pool, service_id)
    service_name = service["name"] if service else ""
    await state.set_state(BookingStates.quick_waiting_name)
    await state.update_data(quick_service_id=service_id, quick_service_name=service_name)
    from app.handlers._utils import edit_or_replace
    msg = await edit_or_replace(
        callback,
        f"⚡ <b>Швидке замовлення</b>\n🎯 {service_name}\n\nВведіть ваше ім'я та прізвище:",
        reply_markup=cancel_kb(),
    )
    await state.update_data(bot_msg_id=msg.message_id)

    await callback.answer()


@router.message(BookingStates.quick_waiting_name)
async def quick_name(message: Message, state: FSMContext, bot: Bot) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
        err = await message.answer("⚠️ Введіть ім'я (мінімум 2 символи)")
        asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
        return

    data = await state.get_data()
    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))

    await state.update_data(full_name=name)
    await state.set_state(BookingStates.quick_waiting_phone)
    sent = await message.answer("📱 Введіть ваш телефон:", reply_markup=_phone_kb())
    await state.update_data(bot_msg_id=sent.message_id)


@router.message(BookingStates.quick_waiting_phone)
async def quick_phone(message: Message, state: FSMContext, bot: Bot, pool: asyncpg.Pool) -> None:
    data = await state.get_data()

    if message.text == "❌ Скасувати":
        await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
        asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
        await state.clear()
        msg = await message.answer("Скасовано.", reply_markup=ReplyKeyboardRemove())
        asyncio.create_task(_delete_after(bot, message.chat.id, msg.message_id))
        await message.answer("Головне меню:", reply_markup=main_menu_kb())
        return

    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    elif message.text:
        phone = message.text.strip()
        if not re.match(r'^[\d\s\+\-\(\)]{10,}$', phone):
            asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
            err = await message.answer(
                "⚠️ Невірний формат. Введіть телефон або натисніть кнопку нижче:",
                reply_markup=_phone_kb(),
            )
            asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
            return
    else:
        asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
        return

    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))

    full_name = data["full_name"]
    service_id = data["quick_service_id"]
    service_name = data["quick_service_name"]

    inquiry_id = await create_inquiry(pool, message.from_user.id, full_name, phone, service_id, service_name)
    await state.clear()

    msg = await message.answer(
        f"✅ <b>Заявку прийнято!</b>\n🎯 {service_name}\n\nМи зателефонуємо вам найближчим часом.",
        reply_markup=ReplyKeyboardRemove(),
    )
    asyncio.create_task(_delete_after(bot, message.chat.id, msg.message_id, delay=30.0))
    await message.answer("Головне меню:", reply_markup=main_menu_kb())

    await _notify_admin_inquiry(bot, inquiry_id, full_name, phone, service_name)


# --- Helpers ---

def _fmt_date(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


def _services_lines(cart_items: list) -> list[str]:
    if not cart_items:
        return ["\nПослуги не обрані"]
    lines = ["\n<b>Послуги:</b>"]
    total = 0
    for item in cart_items:
        price, qty = item["price"], item["quantity"]
        if price:
            total += price * qty
            lines.append(f"• {item['name']} — {price:.0f} грн × {qty}")
        else:
            lines.append(f"• {item['name']} × {qty}")
    if total:
        lines.append(f"\n💰 Разом: {total:.0f} грн")
    return lines


def _confirmation_text(data: dict, cart_items: list) -> str:
    lines = [
        "📋 <b>Підтвердження бронювання</b>\n",
        f"👤 {data['full_name']}",
        f"📱 {data['phone']}",
        f"👶 Дітей: {data['children_count']}",
        f"📆 Дата: {_fmt_date(data['booking_date'])}",
    ]
    lines.extend(_services_lines(cart_items))
    return "\n".join(lines)


async def _notify_admin(bot: Bot, booking_id: int, data: dict, cart_items: list) -> None:
    if not _config.admin_chat_id:
        return
    lines = [
        f"📅 Нове бронювання #{booking_id}",
        f"👤 {data['full_name']}",
        f"📱 {data['phone']}",
        f"👶 Дітей: {data['children_count']}",
        f"📆 Дата: {_fmt_date(data['booking_date'])}",
    ]
    if cart_items:
        lines.append("\nПослуги:")
        total = 0
        for item in cart_items:
            price, qty = item["price"], item["quantity"]
            if price:
                total += price * qty
                lines.append(f"• {item['name']} — {price:.0f} грн × {qty}")
            else:
                lines.append(f"• {item['name']} × {qty}")
        if total:
            lines.append(f"\n💰 Разом: {total:.0f} грн")
    else:
        lines.append("\nПослуги не обрані")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"adm:ok:{booking_id}"),
        InlineKeyboardButton(text="❌ Відхилити",   callback_data=f"adm:no:{booking_id}"),
    ]])
    try:
        await bot.send_message(_config.admin_chat_id, "\n".join(lines), parse_mode=None, reply_markup=kb)
    except Exception as e:
        logger.error("Failed to notify admin: %s", e)


async def _notify_admin_cancelled(bot: Bot, booking: dict, reason: str = "") -> None:
    if not _config.admin_chat_id:
        return
    date_str = booking["booking_date"].strftime("%d.%m.%Y")
    text = (
        f"❌ Бронювання #{booking['id']} скасовано клієнтом\n"
        f"👤 {booking['full_name']}\n"
        f"📱 {booking['phone']}\n"
        f"👶 Дітей: {booking['children_count']}\n"
        f"📆 Дата: {date_str}"
    )
    if reason:
        text += f"\n💬 Причина: {reason}"
    try:
        await bot.send_message(_config.admin_chat_id, text, parse_mode=None)
    except Exception as e:
        logger.error("Failed to notify admin about cancellation: %s", e)


async def _notify_client_from_bot(bot: Bot, telegram_id: int, booking_id: int, booking_date, new_status: str) -> None:
    date_str = booking_date.strftime("%d.%m.%Y")
    if new_status == "confirmed":
        text = f"✅ Ваше бронювання #{booking_id} на {date_str} підтверджено!\nЧекаємо вас! 🎉"
    else:
        text = f"❌ Ваше бронювання #{booking_id} на {date_str} скасовано.\nЗверніться до нас для уточнень."
    try:
        await bot.send_message(telegram_id, text)
    except Exception as e:
        logger.error("Failed to notify client %s: %s", telegram_id, e)


async def _notify_admin_inquiry(
    bot: Bot, inquiry_id: int, full_name: str, phone: str, service_name: str
) -> None:
    if not _config.admin_chat_id:
        return
    text = (
        f"⚡ Нова заявка #{inquiry_id}\n"
        f"🎯 {service_name}\n"
        f"👤 {full_name}\n"
        f"📱 {phone}"
    )
    try:
        await bot.send_message(_config.admin_chat_id, text, parse_mode=None)
    except Exception as e:
        logger.error("Failed to notify admin about inquiry: %s", e)


# --- My bookings ---

_STATUS_LABELS = {
    "new":       "🔵 Нове",
    "confirmed": "✅ Підтверджено",
    "cancelled": "⛔ Скасовано",
}

_CANCEL_REASONS = {
    "plans": "🔄 Змінились плани",
    "sick":  "🤒 Захворіли",
    "date":  "📅 Обрали іншу дату",
}


def _cancel_reason_kb(booking_id: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=f"booking:cancel_reason:{booking_id}:{key}")]
            for key, label in _CANCEL_REASONS.items()]
    rows.append([InlineKeyboardButton(text="📝 Інша причина", callback_data=f"booking:cancel_reason:{booking_id}:other")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="booking:my")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _my_bookings_kb(bookings: list) -> InlineKeyboardMarkup:
    rows = []
    for b in bookings:
        if b["status"] != "cancelled":
            row = [InlineKeyboardButton(
                text=f"✏️ Змінити #{b['id']}",
                callback_data=f"booking:change:{b['id']}",
            )]
            if b["status"] == "new":
                row.append(InlineKeyboardButton(
                    text=f"❌ Скасувати #{b['id']}",
                    callback_data=f"booking:user_cancel:{b['id']}",
                ))
            rows.append(row)
    rows.append([InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _my_bookings_text(bookings: list) -> str:
    if not bookings:
        return "📋 У вас ще немає бронювань."
    lines = ["📋 <b>Ваші бронювання:</b>\n"]
    for b in bookings:
        date_str = b["booking_date"].strftime("%d.%m.%Y")
        status = _STATUS_LABELS.get(b["status"], b["status"])
        lines.append(f"<b>#{b['id']}</b>  📅 {date_str}  {status}")
        lines.append(f"👶 Дітей: {b['children_count']}")
        if b["services_summary"]:
            lines.append(f"🗂 {b['services_summary']}")
        lines.append("")
    return "\n".join(lines).strip()


@router.callback_query(F.data == "booking:my")
async def my_bookings(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    bookings = await get_user_bookings(pool, callback.from_user.id)
    await callback.message.edit_text(
        _my_bookings_text(bookings),
        reply_markup=_my_bookings_kb(bookings),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("booking:user_cancel:"))
async def user_cancel_booking(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    booking_id = int(callback.data.split(":")[2])
    await callback.message.edit_text(
        f"Вкажіть причину скасування бронювання #{booking_id}:",
        reply_markup=_cancel_reason_kb(booking_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("booking:cancel_reason:"))
async def user_cancel_with_reason(
    callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool, bot: Bot
) -> None:
    parts = callback.data.split(":")          # ["booking","cancel_reason","id","key"]
    booking_id = int(parts[2])
    reason_key = parts[3]

    if reason_key == "other":
        await state.set_state(BookingStates.waiting_cancel_reason)
        await state.update_data(pending_cancel_id=booking_id, bot_msg_id=callback.message.message_id)
        await callback.message.edit_text(
            "📝 Напишіть причину скасування одним повідомленням:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад", callback_data=f"booking:user_cancel:{booking_id}")],
            ]),
        )
        await callback.answer()
        return

    reason = _CANCEL_REASONS.get(reason_key, "")
    await _do_cancel_booking(callback.message, pool, bot, booking_id, callback.from_user.id, reason)
    await callback.answer()


@router.message(BookingStates.waiting_cancel_reason)
async def user_cancel_reason_text(message: Message, state: FSMContext, pool: asyncpg.Pool, bot: Bot) -> None:
    reason = (message.text or "").strip()
    data = await state.get_data()
    booking_id = data.get("pending_cancel_id")
    bot_msg_id = data.get("bot_msg_id")
    await state.clear()
    asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))

    if not reason:
        return

    async def _edit(text: str, kb=None) -> None:
        try:
            await bot.edit_message_text(text, chat_id=message.chat.id, message_id=bot_msg_id, reply_markup=kb)
        except Exception:
            await message.answer(text, reply_markup=kb)

    row = await pool.fetchrow(
        """
        UPDATE bookings SET status='cancelled'
        WHERE id=$1 AND telegram_id=$2 AND status='new'
        RETURNING id, full_name, phone, children_count, booking_date
        """,
        booking_id, message.from_user.id,
    )
    if row:
        await _notify_admin_cancelled(bot, dict(row), reason)

    bookings = await get_user_bookings(pool, message.from_user.id)
    await _edit(_my_bookings_text(bookings), _my_bookings_kb(bookings))


# --- Booking change flow ---

@router.callback_query(F.data.startswith("booking:change:"))
async def change_booking_start(
    callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool
) -> None:
    booking_id = int(callback.data.split(":")[2])
    booking = await get_booking_by_id(pool, booking_id)

    if not booking or booking["telegram_id"] != callback.from_user.id:
        await callback.answer("Бронювання не знайдено", show_alert=True)
        return
    if booking["status"] == "cancelled":
        await callback.answer("Скасоване бронювання не можна змінювати", show_alert=True)
        return

    pending = await get_pending_change_for_booking(pool, booking_id)
    if pending:
        await callback.answer("Вже є незавершений запит на зміну. Очікуйте відповіді адміністратора.", show_alert=True)
        return

    await cart_clear(pool, callback.from_user.id)
    existing_items = await get_booking_items(pool, booking_id)
    for item in existing_items:
        for _ in range(item["quantity"]):
            await cart_add(pool, callback.from_user.id, item["service_id"])

    await state.set_state(ChangeStates.waiting_date)
    await state.update_data(
        booking_id=booking_id,
        orig_date=booking["booking_date"].isoformat(),
        orig_children=booking["children_count"],
    )

    days = int(await get_setting(pool, "booking_days_ahead", "14"))
    blocked = await get_blocked_dates(pool)
    blocked_weekdays = await get_blocked_weekdays(pool)
    sent = await callback.message.edit_text(
        f"✏️ <b>Зміна бронювання #{booking_id}</b>\n\nОберіть нову дату:",
        reply_markup=date_selection_kb(days, blocked, blocked_weekdays, prefix="change"),
    )
    await state.update_data(bot_msg_id=sent.message_id)
    await callback.answer()


@router.callback_query(F.data == "change:noop")
async def change_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("change:cal:"), ChangeStates.waiting_date)
async def change_calendar_nav(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    parts = callback.data.split(":")
    year, month = int(parts[2]), int(parts[3])
    blocked = await get_blocked_dates(pool)
    blocked_weekdays = await get_blocked_weekdays(pool)
    await callback.message.edit_reply_markup(
        reply_markup=calendar_kb(year, month, blocked, blocked_weekdays, prefix="change")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("change:caldate:"), ChangeStates.waiting_date)
async def change_caldate(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    raw = callback.data.split(":", 2)[2]
    try:
        parsed = dt_date.fromisoformat(raw)
    except ValueError:
        await callback.answer("Невірна дата", show_alert=True)
        return

    today = dt_date.today()
    if parsed < today:
        await callback.answer("Ця дата вже минула", show_alert=True)
        return

    blocked = await get_blocked_dates(pool)
    blocked_wdays = await get_blocked_weekdays(pool)
    if parsed in blocked or parsed.weekday() in blocked_wdays:
        await callback.answer("Ця дата заблокована", show_alert=True)
        return

    await state.update_data(proposed_date=raw)
    await _change_ask_children(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("change:date:"), ChangeStates.waiting_date)
async def change_date_selected(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    from datetime import timedelta
    raw = callback.data.split(":", 2)[2]
    try:
        parsed = dt_date.fromisoformat(raw)
    except ValueError:
        await callback.answer("Невірна дата", show_alert=True)
        return

    today = dt_date.today()
    days_ahead = int(await get_setting(pool, "booking_days_ahead", "14"))
    if not (today <= parsed <= today + timedelta(days=days_ahead)):
        await callback.answer("Ця дата недоступна", show_alert=True)
        return

    blocked = await get_blocked_dates(pool)
    blocked_wdays = await get_blocked_weekdays(pool)
    if parsed in blocked or parsed.weekday() in blocked_wdays:
        await callback.answer("Ця дата заблокована", show_alert=True)
        return

    await state.update_data(proposed_date=raw)
    await _change_ask_children(callback, state)
    await callback.answer()


async def _change_ask_children(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    orig_children = data.get("orig_children", "?")
    sent = await callback.message.edit_text(
        f"👶 Скільки дітей буде? (Поточне: {orig_children})\n\nВведіть число:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="change:cancel")],
        ]),
    )
    await state.update_data(bot_msg_id=sent.message_id)
    await state.set_state(ChangeStates.waiting_children)


@router.message(ChangeStates.waiting_children)
async def change_children(message: Message, state: FSMContext, bot: Bot, pool: asyncpg.Pool) -> None:
    text = (message.text or "").strip()
    try:
        count = int(text)
        if count <= 0:
            raise ValueError
    except ValueError:
        asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))
        err = await message.answer("⚠️ Введіть ціле число більше 0")
        asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
        return

    data = await state.get_data()
    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    asyncio.create_task(_delete_after(bot, message.chat.id, message.message_id))

    await state.update_data(proposed_children=count)
    cart_items = await cart_get(pool, message.from_user.id)
    sent = await message.answer(
        _change_confirm_text(data, count, cart_items),
        reply_markup=confirm_change_kb(),
    )
    await state.update_data(bot_msg_id=sent.message_id)
    await state.set_state(ChangeStates.confirming)


def _change_confirm_text(data: dict, proposed_children: int, cart_items: list) -> str:
    booking_id = data.get("booking_id")
    orig_date = data.get("orig_date", "")
    proposed_date = data.get("proposed_date", "")
    orig_children = data.get("orig_children", "?")
    lines = [
        f"✏️ <b>Запит на зміну бронювання #{booking_id}</b>\n",
        f"📆 Дата: {_fmt_date(orig_date)} → {_fmt_date(proposed_date)}",
        f"👶 Дітей: {orig_children} → {proposed_children}",
    ]
    lines.extend(_services_lines(cart_items))
    lines.append("\nНатисніть «Надіслати запит» для відправки адміністратору.")
    return "\n".join(lines)


@router.callback_query(F.data == "change:resume_confirm")
async def change_resume_confirm(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    data = await state.get_data()
    if not data.get("booking_id"):
        await callback.message.edit_text("Сесія застаріла. Почніть знову.", reply_markup=main_menu_kb())
        await state.clear()
        await callback.answer()
        return
    proposed_children = data.get("proposed_children", data.get("orig_children", 1))
    cart_items = await cart_get(pool, callback.from_user.id)
    await callback.message.edit_text(
        _change_confirm_text(data, proposed_children, cart_items),
        reply_markup=confirm_change_kb(),
    )
    await state.set_state(ChangeStates.confirming)
    await callback.answer()


@router.callback_query(F.data == "change:cancel")
async def change_cancel(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    await cart_clear(pool, callback.from_user.id)
    await state.clear()
    await callback.message.edit_text("Зміну скасовано.", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "change:confirm")
async def change_confirm(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool, bot: Bot) -> None:
    await callback.answer()
    data = await state.get_data()
    booking_id = data.get("booking_id")
    proposed_date_str = data.get("proposed_date")
    proposed_children = data.get("proposed_children")

    if not booking_id or not proposed_date_str or not proposed_children:
        await callback.message.edit_text("Сесія застаріла. Почніть знову.", reply_markup=main_menu_kb())
        await state.clear()
        return

    cart_items = await cart_get(pool, callback.from_user.id)
    proposed_date = dt_date.fromisoformat(proposed_date_str)

    request_id = await create_change_request(pool, booking_id, proposed_date, proposed_children)
    await create_change_items(pool, request_id, cart_items)
    await cart_clear(pool, callback.from_user.id)
    await state.clear()

    booking = await get_booking_by_id(pool, booking_id)
    if booking:
        await _notify_admin_change_request(bot, request_id, booking, data, proposed_date_str, proposed_children, cart_items)

    await callback.message.edit_text(
        f"✅ Запит на зміну бронювання #{booking_id} надіслано!\nОчікуйте підтвердження адміністратора.",
        reply_markup=main_menu_kb(),
    )


async def _notify_admin_change_request(
    bot: Bot,
    request_id: int,
    booking: asyncpg.Record,
    data: dict,
    proposed_date_str: str,
    proposed_children: int,
    cart_items: list,
) -> None:
    if not _config.admin_chat_id:
        return
    booking_id = booking["id"]
    orig_date_str = data.get("orig_date", "")
    orig_children = data.get("orig_children", "?")
    lines = [
        f"✏️ Запит на зміну бронювання #{booking_id}",
        f"👤 {booking['full_name']}",
        f"📱 {booking['phone']}",
        f"📆 Дата: {_fmt_date(orig_date_str)} → {_fmt_date(proposed_date_str)}",
        f"👶 Дітей: {orig_children} → {proposed_children}",
    ]
    if cart_items:
        lines.append("\nНові послуги:")
        total = 0
        for item in cart_items:
            price, qty = item["price"], item["quantity"]
            if price:
                total += price * qty
                lines.append(f"• {item['name']} — {price:.0f} грн × {qty}")
            else:
                lines.append(f"• {item['name']} × {qty}")
        if total:
            lines.append(f"\n💰 Разом: {total:.0f} грн")
    else:
        lines.append("\nПослуги не обрані")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Прийняти", callback_data=f"adm:chg_ok:{request_id}"),
        InlineKeyboardButton(text="❌ Відхилити", callback_data=f"adm:chg_no:{request_id}"),
    ]])
    try:
        await bot.send_message(_config.admin_chat_id, "\n".join(lines), parse_mode=None, reply_markup=kb)
    except Exception as e:
        logger.error("Failed to notify admin about change request: %s", e)


async def _notify_client_change_result(
    bot: Bot, telegram_id: int, booking_id: int, proposed_date, approved: bool
) -> None:
    date_str = proposed_date.strftime("%d.%m.%Y") if hasattr(proposed_date, "strftime") else str(proposed_date)
    if approved:
        text = f"✅ Зміну бронювання #{booking_id} підтверджено!\nНова дата: {date_str} 🎉"
    else:
        text = f"❌ Зміну бронювання #{booking_id} відхилено.\nОригінальне бронювання залишається в силі."
    try:
        await bot.send_message(telegram_id, text)
    except Exception as e:
        logger.error("Failed to notify client %s about change result: %s", telegram_id, e)


@router.callback_query(F.data.startswith("adm:chg_"))
async def admin_change_action(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    if callback.message.chat.id != _config.admin_chat_id:
        await callback.answer()
        return

    parts = callback.data.split(":", 2)
    action_str = parts[1]   # "chg_ok" or "chg_no"
    request_id = int(parts[2])
    approve = action_str == "chg_ok"

    change_req = await get_change_request(pool, request_id)
    if not change_req or change_req["status"] != "pending":
        await callback.answer("Вже оброблено")
        return

    if approve:
        await apply_change_request(pool, request_id)

    new_status = "approved" if approve else "rejected"
    await update_change_request_status(pool, request_id, new_status)

    booking = await get_booking_by_id(pool, change_req["booking_id"])
    if booking:
        await _notify_client_change_result(
            callback.bot, booking["telegram_id"],
            change_req["booking_id"], change_req["proposed_date"], approve,
        )

    label = "✅ Зміни прийнято" if approve else "❌ Зміни відхилено"
    original_text = callback.message.text or ""
    await callback.message.edit_text(f"{original_text}\n\n{label}", reply_markup=None)
    await callback.answer(label)


@router.callback_query(F.data.startswith("adm:"))
async def admin_booking_action(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    if callback.message.chat.id != _config.admin_chat_id:
        await callback.answer()
        return

    _, action, bid_str = callback.data.split(":", 2)
    booking_id = int(bid_str)
    new_status = "confirmed" if action == "ok" else "cancelled"

    booking = await get_booking_by_id(pool, booking_id)
    if not booking:
        await callback.answer("Бронювання не знайдено")
        return
    if booking["status"] != "new":
        label = "✅ Підтверджено" if booking["status"] == "confirmed" else "❌ Скасовано"
        await callback.answer(f"Вже оброблено: {label}")
        return

    await update_booking_status(pool, booking_id, new_status)
    await _notify_client_from_bot(callback.bot, booking["telegram_id"], booking_id, booking["booking_date"], new_status)

    label = "✅ Підтверджено" if new_status == "confirmed" else "❌ Відхилено"
    original_text = callback.message.text or ""
    await callback.message.edit_text(f"{original_text}\n\n{label}", reply_markup=None)
    await callback.answer(label)


async def _do_cancel_booking(
    msg, pool: asyncpg.Pool, bot: Bot, booking_id: int, user_id: int, reason: str
) -> None:
    row = await pool.fetchrow(
        """
        UPDATE bookings SET status='cancelled'
        WHERE id=$1 AND telegram_id=$2 AND status='new'
        RETURNING id, full_name, phone, children_count, booking_date
        """,
        booking_id, user_id,
    )
    if row:
        await _notify_admin_cancelled(bot, dict(row), reason)

    bookings = await get_user_bookings(pool, user_id)
    await msg.edit_text(_my_bookings_text(bookings), reply_markup=_my_bookings_kb(bookings))
