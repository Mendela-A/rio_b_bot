import asyncio
import logging
from datetime import date, timedelta

import asyncpg
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message

from app.config import load_config
from app.database.queries import get_stats, get_bookings_in_range, get_bookings_new

router = Router()
logger = logging.getLogger(__name__)
_config = load_config()

_AUTO_DELETE_DELAY = 60  # seconds


async def _answer_autodelete(message: Message, text: str, delay: int = _AUTO_DELETE_DELAY, **kwargs) -> None:
    sent = await message.answer(text, **kwargs)
    await asyncio.sleep(delay)
    try:
        await sent.delete()
        await message.delete()
    except Exception:
        pass

_STATUS_LABELS = {
    "new": "🔵",
    "confirmed": "✅",
    "cancelled": "⛔",
}


async def is_admin(bot: Bot, user_id: int) -> bool:
    if not _config.admin_chat_id:
        return False
    try:
        member = await bot.get_chat_member(_config.admin_chat_id, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


def _fmt_stats(s) -> str:
    return (
        "📊 <b>Статистика РІО</b>\n\n"
        f"📋 Бронювань всього: <b>{s['total_bookings']}</b>\n"
        f"  🔵 Нових: {s['count_new']}\n"
        f"  ✅ Підтверджених: {s['count_confirmed']}\n"
        f"  ⛔ Скасованих: {s['count_cancelled']}\n\n"
        f"⚡ Швидких заявок: <b>{s['total_inquiries']}</b>"
    )


def _fmt_bookings_list(bookings, title: str) -> str:
    if not bookings:
        return f"{title}\n\n(немає бронювань)"
    lines = [f"{title}\n"]
    for b in bookings:
        icon = _STATUS_LABELS.get(b["status"], "❓")
        lines.append(f"{icon} <b>#{b['id']}</b> — {b['full_name']}")
        lines.append(f"📱 {b['phone']}  👶 {b['children_count']} дит.")
        lines.append(f"📅 {b['booking_date'].strftime('%d.%m.%Y')}")
        if b["services_summary"]:
            lines.append(f"🗂 {b['services_summary']}")
        lines.append("")
    return "\n".join(lines).strip()


@router.message(Command("admin"))
async def cmd_admin(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.from_user.id):
        return
    asyncio.create_task(_answer_autodelete(
        message,
        "⚙️ <b>Адмін-панель РІО</b>\n\n"
        "📊 Статистика — загальна статистика\n"
        "🔵 Непідтверджені — нові заявки\n"
        "📅 Бронювання сьогодні — хто прийде\n"
        "📅 Тиждень — наступні 7 днів\n"
        "📢 Розсилка — (в розробці)\n"
        "⚙ Налаштування — (в розробці)",
    ))


@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message, bot: Bot, pool: asyncpg.Pool) -> None:
    if not await is_admin(bot, message.from_user.id):
        return
    asyncio.create_task(_answer_autodelete(message, _fmt_stats(await get_stats(pool))))


@router.message(F.text == "🔵 Непідтверджені")
async def admin_bookings_new(message: Message, bot: Bot, pool: asyncpg.Pool) -> None:
    if not await is_admin(bot, message.from_user.id):
        return
    bookings = await get_bookings_new(pool)
    asyncio.create_task(_answer_autodelete(message, _fmt_bookings_list(bookings, "🔵 Непідтверджені бронювання")))


@router.message(F.text == "📅 Бронювання сьогодні")
async def admin_bookings_today(message: Message, bot: Bot, pool: asyncpg.Pool) -> None:
    if not await is_admin(bot, message.from_user.id):
        return
    today = date.today()
    bookings = await get_bookings_in_range(pool, today, today)
    asyncio.create_task(_answer_autodelete(message, _fmt_bookings_list(bookings, f"📅 Сьогодні, {today.strftime('%d.%m.%Y')}")))


@router.message(F.text == "📅 Тиждень")
async def admin_bookings_week(message: Message, bot: Bot, pool: asyncpg.Pool) -> None:
    if not await is_admin(bot, message.from_user.id):
        return
    today = date.today()
    end = today + timedelta(days=6)
    bookings = await get_bookings_in_range(pool, today, end)
    asyncio.create_task(_answer_autodelete(message, _fmt_bookings_list(bookings, f"📅 Тиждень: {today.strftime('%d.%m')}–{end.strftime('%d.%m.%Y')}")))


@router.message(F.text == "📢 Розсилка")
async def admin_broadcast(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.from_user.id):
        return
    asyncio.create_task(_answer_autodelete(message, "📢 Розсилка — в розробці 🔧"))


@router.message(F.text == "⚙ Налаштування")
async def admin_settings(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.from_user.id):
        return
    asyncio.create_task(_answer_autodelete(message, "⚙ Налаштування — в розробці 🔧"))
