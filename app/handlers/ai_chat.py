import asyncio
import logging
import os
import time

import anthropic
import asyncpg
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.database.queries import (
    get_ai_qa_pairs,
    get_services_for_ai,
    get_ai_history,
    append_ai_history,
    clear_ai_history,
    trim_ai_history,
    log_ai_usage,
    get_setting,
    get_ai_history_last_age_hours,
)
from app import texts
from app.keyboards.main_menu import main_menu_kb

logger = logging.getLogger(__name__)
router = Router()

_MSG_TTL = 5.0


async def _delete_after(message, delay: float = _MSG_TTL) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

AI_COOLDOWN_SECONDS = 5


class AIChatStates(StatesGroup):
    chatting = State()


def _end_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Завершити чат", callback_data="ai:end")]
    ])


_DEFAULT_NO_ANSWER_PHRASE = "немає цієї інформації"

_DEFAULT_SYSTEM_PROMPT = (
    "Ти — асистент {description}\n"
    "Правила (обов'язкові):\n"
    "1. Відповідай ВИКЛЮЧНО на основі бази знань нижче.\n"
    "2. Якщо інформації немає — НЕ вигадуй. Використай фразу: «{no_answer_phrase}»\n"
    "3. Не придумуй ціни, дати, умови яких немає в базі.\n"
    "4. Відповідай українською мовою, коротко і ввічливо.\n"
    "5. Пиши правильною українською. Заборонені слова та їх заміни: "
    "«розповідають» (не «розповідять»), «розкажіть» (не «розповідіть»), "
    "«замовити» (не «заказати»), «захід» (не «мероприємство»).\n"
    "6. ЗАБОРОНЕНО будь-яке форматування тексту. Не використовуй: зірочки (* або **), "
    "підкреслення (_), решітку (#), зворотні лапки (`). Пиши ТІЛЬКИ звичайний текст без будь-яких спецсимволів.\n"
    "7. Не починай відповідь зі звернення типу «Звісно!», «Авжеж!», «Зрозуміло!» тощо.\n"
    "8. Будь ТОЧНИМ у назвах категорій та послуг. "
    "Кожна категорія має окремі ціни й умови — ніколи не переноси інформацію між ними. "
    "Наприклад: «Аніматор на годину» і «Аніматор на виїзд» — це різні послуги з різними умовами та цінами.\n"
    "9. Якщо клієнт питає про послугу загально (наприклад, «які є аніматори?», «що є для дітей?»), "
    "— перелічуй ВСІ відповідні категорії з бази знань, не обмежуйся однією. "
    "Показуй кожну категорію окремо з її послугами та цінами."
)


def _build_catalog(services: list) -> str:
    children: dict[int, list] = {}

    for s in services:
        if s["parent_id"] is not None:
            children.setdefault(s["parent_id"], []).append(s)

    by_category: dict[str, list] = {}
    for s in services:
        if s["parent_id"] is not None:
            continue
        cat = s["category_name"]
        if cat not in by_category:
            by_category[cat] = []
        kids = children.get(s["id"], [])
        if kids:
            by_category[cat].append(f'  {s["name"]}:')
            for k in kids:
                price = f'{int(k["price"])} грн' if k["price"] else "ціна за запитом"
                desc = f' — {k["description"]}' if k["description"] else ""
                by_category[cat].append(f'    • {k["name"]}: {price}{desc}')
        else:
            price = f'{int(s["price"])} грн' if s["price"] else "ціна за запитом"
            desc = f' — {s["description"]}' if s["description"] else ""
            by_category[cat].append(f'  • {s["name"]}: {price}{desc}')

    lines = []
    for cat, items in by_category.items():
        lines.append(f"--- {cat} ---")
        lines.extend(items)
        lines.append("")
    return "\n".join(lines)


def _build_system_prompt(template: str, description: str, qa_pairs: list, no_answer_phrase: str, services: list) -> str:
    # str.replace замість .format() — безпечно якщо адмін напише {щось} у промпті
    rules = template.replace("{description}", description).replace("{no_answer_phrase}", no_answer_phrase)
    parts = [rules]

    catalog = _build_catalog(services)
    if catalog:
        parts.append(f"=== КАТАЛОГ ПОСЛУГ ===\n{catalog}")

    qa_block = "\n".join(
        f"Питання: {p['question']}\nВідповідь: {p['answer']}"
        for p in qa_pairs
    )
    if qa_block:
        parts.append(f"=== БАЗА ЗНАНЬ (Q&A) ===\n{qa_block}")

    return "\n\n".join(parts)


@router.callback_query(F.data == "ai:start")
async def start_ai_chat(callback: CallbackQuery, state: FSMContext, pool: asyncpg.Pool) -> None:
    # Якщо вже в чаті — просто підтверджуємо callback, не скидаємо стан
    current = await state.get_state()
    if current == AIChatStates.chatting:
        await callback.answer()
        return

    ai_enabled = await get_setting(pool, "ai_enabled", "true")
    if ai_enabled.lower() != "true":
        await callback.answer("Асистент тимчасово недоступний.", show_alert=True)
        return

    user_id = callback.from_user.id
    ttl_hours = int(await get_setting(pool, "ai_history_ttl_hours", "24"))
    age = await get_ai_history_last_age_hours(pool, user_id)
    if age is None or age > ttl_hours:
        await clear_ai_history(pool, user_id)

    welcome = await get_setting(pool, "ai_welcome_message", "Привіт! Напишіть ваше запитання.")
    await state.set_state(AIChatStates.chatting)
    await state.update_data(bot_msg_id=callback.message.message_id)
    await callback.message.edit_text(welcome, reply_markup=_end_kb())
    await callback.answer()


@router.callback_query(F.data == "ai:end")
async def end_ai_chat(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.get("menu.greeting"), reply_markup=main_menu_kb())
    await callback.answer()


@router.message(AIChatStates.chatting)
async def handle_ai_message(message: Message, state: FSMContext, pool: asyncpg.Pool, bot: Bot) -> None:
    user_id = message.from_user.id
    user_text = (message.text or "").strip()

    if not user_text:
        return

    # Rate limit: не частіше ніж раз на AI_COOLDOWN_SECONDS секунд
    data = await state.get_data()
    last_request_at = data.get("last_request_at", 0)
    now = time.monotonic()
    if now - last_request_at < AI_COOLDOWN_SECONDS:
        wait = int(AI_COOLDOWN_SECONDS - (now - last_request_at)) + 1
        asyncio.create_task(_delete_after(message))
        await _update_or_send(bot, message.chat.id, state,
                              f"⏳ Зачекайте {wait} сек. перед наступним запитанням.")
        return

    asyncio.create_task(_delete_after(message))

    await bot.send_chat_action(message.chat.id, "typing")

    ai_enabled = await get_setting(pool, "ai_enabled", "true")
    if ai_enabled.lower() != "true":
        await _update_or_send(bot, message.chat.id, state,
                              "Асистент тимчасово недоступний. Спробуйте пізніше.")
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY is not set")
        await _update_or_send(bot, message.chat.id, state,
                              "Помилка конфігурації. Зверніться до адміністратора.")
        return

    history_limit = int(await get_setting(pool, "ai_history_limit", "20"))
    max_tokens = int(await get_setting(pool, "ai_max_tokens", "1024"))
    description = await get_setting(pool, "ai_company_description", "розважальний заклад")
    prompt_template = await get_setting(pool, "ai_system_prompt", _DEFAULT_SYSTEM_PROMPT)
    model = await get_setting(pool, "ai_model", "claude-haiku-4-5-20251001")
    no_answer_phrase = await get_setting(pool, "ai_no_answer_phrase", _DEFAULT_NO_ANSWER_PHRASE)

    history = await get_ai_history(pool, user_id, limit=history_limit)
    qa_pairs = await get_ai_qa_pairs(pool)
    services = await get_services_for_ai(pool)

    system_prompt = _build_system_prompt(prompt_template, description, qa_pairs, no_answer_phrase, services)
    messages = [{"role": r["role"], "content": r["content"]} for r in history]
    messages.append({"role": "user", "content": user_text})

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        t0 = time.monotonic()
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=messages,
        )
        response_ms = int((time.monotonic() - t0) * 1000)
        reply_text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cache_write = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    except Exception as e:
        logger.error("Anthropic API error: %s", e)
        await _update_or_send(bot, message.chat.id, state,
                              "Виникла помилка. Спробуйте пізніше або зверніться до адміністратора.")
        return

    await append_ai_history(pool, user_id, "user", user_text)
    await append_ai_history(pool, user_id, "assistant", reply_text)
    await trim_ai_history(pool, user_id, history_limit)
    await log_ai_usage(pool, user_id, input_tokens, output_tokens, cache_write, cache_read,
                       response_ms=response_ms, model=model)
    await state.update_data(last_request_at=time.monotonic())

    await _update_or_send(bot, message.chat.id, state, reply_text)


async def _update_or_send(bot: Bot, chat_id: int, state: FSMContext, text: str) -> None:
    """Редагує існуюче повідомлення бота, якщо можливо — інакше надсилає нове.

    parse_mode=None: AI-відповідь — довільний текст, може містити <, >, &
    які зламають HTML-рендеринг (глобальний дефолт бота — ParseMode.HTML).
    """
    data = await state.get_data()
    bot_msg_id = data.get("bot_msg_id")
    if bot_msg_id:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=bot_msg_id,
                reply_markup=_end_kb(), parse_mode=None,
            )
            return
        except Exception:
            pass
    msg = await bot.send_message(chat_id, text, reply_markup=_end_kb(), parse_mode=None)
    await state.update_data(bot_msg_id=msg.message_id)
