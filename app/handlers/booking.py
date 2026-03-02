from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.keyboards.main_menu import main_menu_kb

router = Router()


@router.callback_query(F.data == "booking")
async def booking_stub(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🔧 Функція бронювання в розробці.\nОчікуйте незабаром!",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
