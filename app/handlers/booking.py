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
    cart_get, cart_clear, create_booking, create_booking_items, get_user_bookings,
    get_service_by_id, create_inquiry,
)
from app.keyboards.booking_kb import cancel_kb, date_selection_kb, confirm_booking_kb, cart_kb
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
        await message.delete()
        err = await message.answer("⚠️ Введіть ім'я (мінімум 2 символи)")
        asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
        return

    data = await state.get_data()
    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    await message.delete()

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
        await message.delete()
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
            await message.delete()
            err = await message.answer(
                "⚠️ Невірний формат. Введіть телефон або натисніть кнопку нижче:",
                reply_markup=_phone_kb(),
            )
            asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
            return
    else:
        await message.delete()
        return

    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    await message.delete()

    await state.update_data(phone=phone)
    await state.set_state(BookingStates.waiting_children)
    sent = await message.answer(texts.get("booking.ask_children"), reply_markup=cancel_kb())
    await state.update_data(bot_msg_id=sent.message_id)


# --- Step 3: children count ---

@router.message(BookingStates.waiting_children)
async def booking_children(message: Message, state: FSMContext, bot: Bot) -> None:
    text = message.text.strip() if message.text else ""
    try:
        count = int(text)
        if count <= 0:
            raise ValueError
    except ValueError:
        await message.delete()
        err = await message.answer("⚠️ Введіть ціле число більше 0")
        asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
        return

    data = await state.get_data()
    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    await message.delete()

    await state.update_data(children_count=count)
    await state.set_state(BookingStates.waiting_date)
    sent = await message.answer(texts.get("booking.ask_date"), reply_markup=date_selection_kb())
    await state.update_data(bot_msg_id=sent.message_id)


# --- Step 4: date selection ---

@router.callback_query(F.data.startswith("booking:date:"), BookingStates.waiting_date)
async def booking_date(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    booking_date = callback.data.split(":", 2)[2]
    await state.update_data(booking_date=booking_date)

    data = await state.get_data()
    cart_items = await cart_get(pool, callback.from_user.id)

    await callback.message.edit_text(_confirmation_text(data, cart_items), reply_markup=confirm_booking_kb())
    await state.update_data(bot_msg_id=callback.message.message_id)
    await callback.answer()


# --- View cart from booking confirmation ---

@router.callback_query(F.data == "booking:view_cart")
async def booking_view_cart(callback: CallbackQuery, pool: asyncpg.Pool) -> None:
    items = await cart_get(pool, callback.from_user.id)
    if not items:
        await callback.message.edit_text(
            "🛒 Кошик порожній.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
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
    await state.update_data(
        quick_service_id=service_id,
        quick_service_name=service_name,
        bot_msg_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        f"⚡ <b>Швидке замовлення</b>\n🎯 {service_name}\n\nВведіть ваше ім'я та прізвище:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(BookingStates.quick_waiting_name)
async def quick_name(message: Message, state: FSMContext, bot: Bot) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.delete()
        err = await message.answer("⚠️ Введіть ім'я (мінімум 2 символи)")
        asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
        return

    data = await state.get_data()
    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    await message.delete()

    await state.update_data(full_name=name)
    await state.set_state(BookingStates.quick_waiting_phone)
    sent = await message.answer("📱 Введіть ваш телефон:", reply_markup=_phone_kb())
    await state.update_data(bot_msg_id=sent.message_id)


@router.message(BookingStates.quick_waiting_phone)
async def quick_phone(message: Message, state: FSMContext, bot: Bot, pool: asyncpg.Pool) -> None:
    data = await state.get_data()

    if message.text == "❌ Скасувати":
        await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
        await message.delete()
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
            await message.delete()
            err = await message.answer(
                "⚠️ Невірний формат. Введіть телефон або натисніть кнопку нижче:",
                reply_markup=_phone_kb(),
            )
            asyncio.create_task(_delete_after(bot, message.chat.id, err.message_id))
            return
    else:
        await message.delete()
        return

    await _try_delete(bot, message.chat.id, data.get("bot_msg_id"))
    await message.delete()

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
    try:
        await bot.send_message(_config.admin_chat_id, "\n".join(lines), parse_mode=None)
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
        if b["status"] == "new":
            rows.append([InlineKeyboardButton(
                text=f"❌ Скасувати #{b['id']}",
                callback_data=f"booking:user_cancel:{b['id']}",
            )])
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
    await message.delete()

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
