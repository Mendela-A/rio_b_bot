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

from app.config import load_config
from app.database.queries import cart_get, cart_clear, create_booking, create_booking_items
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
    await callback.message.edit_text("📝 Введіть прізвище та ім'я:", reply_markup=cancel_kb())
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
        "📱 Введіть номер телефону або натисніть кнопку нижче:",
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
    sent = await message.answer("👶 Скільки дітей буде на святі?", reply_markup=cancel_kb())
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
    sent = await message.answer("📅 Оберіть дату:", reply_markup=date_selection_kb())
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
        f"✅ Бронювання #{booking_id} прийнято!\n\nМи зв'яжемося з вами для підтвердження.",
        reply_markup=main_menu_kb(),
    )

    await _notify_admin(bot, booking_id, data, cart_items)


# --- Cancel ---

@router.callback_query(F.data == "booking:cancel")
async def booking_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Бронювання скасовано.", reply_markup=main_menu_kb())
    await callback.answer()


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
