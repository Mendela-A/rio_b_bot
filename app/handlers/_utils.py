import asyncio
import re

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

PHONE_RE = re.compile(r'^[\d\s\+\-\(\)]{10,}$')


async def delete_after(bot: Bot, chat_id: int, message_id: int, delay: float = 10.0) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def fmt_date(iso: str) -> str:
    if not iso or len(iso) < 10:
        return "—"
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


def services_lines(cart_items: list, entry_rate: float = 0, children_count: int = 0) -> list[str]:
    lines = ["\n<b>Вартість:</b>"]
    total = 0

    if entry_rate and children_count:
        entry_total = entry_rate * children_count
        total += entry_total
        lines.append(f"🎟 Вхід: {entry_rate:.0f} грн × {children_count} дітей = {entry_total:.0f} грн")

    if not cart_items:
        if not entry_rate:
            return ["\nПослуги не обрані"]
    else:
        for item in cart_items:
            qty = item["quantity"]
            ppc = float(item.get("price_per_child") or 0)
            price = float(item["price"] or 0)
            if ppc:
                subtotal = ppc * qty
                total += subtotal
                lines.append(f"• {item['name']} — {ppc:.0f} грн/дитина × {qty} = {subtotal:.0f} грн")
            elif price:
                total += price * qty
                lines.append(f"• {item['name']} — {price:.0f} грн × {qty}")
            else:
                lines.append(f"• {item['name']} × {qty}")

    if total:
        lines.append(f"\n💰 Разом: {total:.0f} грн")
    return lines


def _plural_services(n: int) -> str:
    if n == 1:
        return "1 послуга"
    if 2 <= n <= 4:
        return f"{n} послуги"
    return f"{n} послуг"


def cart_text(cart_items: list) -> str:
    lines = [f"🛒 <b>Ваш кошик ({_plural_services(len(cart_items))}):</b>\n"]
    total = 0
    for item in cart_items:
        qty = item["quantity"]
        ppc = float(item.get("price_per_child") or 0)
        price = float(item["price"] or 0)
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


def confirmation_text(data: dict, cart_items: list, entry_rate: float = 0) -> str:
    lines = [
        "📋 <b>Підтвердження бронювання</b>\n",
        f"👤 {data['full_name']}",
        f"📱 {data['phone']}",
        f"👶 Дітей: {data['children_count']}",
        f"👨 Дорослих: {data.get('adults_count', '—')}",
        f"🎂 Іменинник: {data.get('birthday_person_name') or '—'}"
        + (f" ({fmt_date(data['birthday_person_date'])})" if data.get('birthday_person_date') else ""),
        f"📆 Дата: {fmt_date(data['booking_date'])}",
    ]
    lines.extend(services_lines(cart_items, entry_rate, data.get("children_count", 0)))
    return "\n".join(lines)


def inquiry_client_text(service_name: str, full_name: str, phone: str) -> str:
    return (
        f"✅ <b>Заявку прийнято!</b>\n"
        f"🎯 {service_name}\n"
        f"👤 {full_name}\n"
        f"📱 {phone}\n\n"
        f"Менеджер зв'яжеться з вами найближчим часом."
    )


async def edit_or_replace(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    """Edit message text, or delete+send if current message cannot be edited (e.g. photo)."""
    try:
        return await callback.message.edit_text(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )
    except TelegramBadRequest:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        return await callback.message.answer(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )
