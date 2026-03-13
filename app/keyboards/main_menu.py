from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app import texts


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.get("menu.btn_services_venue"),   callback_data="services:venue")],
        [InlineKeyboardButton(text=texts.get("menu.btn_services_offsite"), callback_data="services:offsite")],
        [InlineKeyboardButton(text=texts.get("menu.btn_services_program"), callback_data="services:program")],
        [
            InlineKeyboardButton(text=texts.get("menu.btn_booking"), callback_data="booking:start"),
            InlineKeyboardButton(text=texts.get("menu.btn_cart"),    callback_data="cart:view"),
        ],
        [InlineKeyboardButton(text=texts.get("menu.btn_my_bookings"), callback_data="booking:my")],
        [InlineKeyboardButton(text=texts.get("menu.btn_info"),         callback_data="info:list")],
        [InlineKeyboardButton(text=texts.get("menu.btn_ai_chat"),      callback_data="ai:start")],
    ])
