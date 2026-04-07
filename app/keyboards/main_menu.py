from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app import texts


def main_menu_kb(cart_count: int = 0, active_bookings: int = 0, has_bookings: bool = False) -> InlineKeyboardMarkup:
    # has_bookings — зворотня сумісність (bool); active_bookings — точний лічильник
    _active = active_bookings if active_bookings else (1 if has_bookings else 0)
    cart_label = f"🛒 Кошик ({cart_count})" if cart_count > 0 else texts.get("menu.btn_cart")
    base_label = texts.get("menu.btn_my_bookings")
    bookings_label = f"{base_label} ({_active})" if _active > 0 else base_label
    rows = [
        [InlineKeyboardButton(text=texts.get("menu.btn_services_venue"),   callback_data="services:venue")],
        [InlineKeyboardButton(text=texts.get("menu.btn_services_offsite"), callback_data="services:offsite")],
        [InlineKeyboardButton(text=texts.get("menu.btn_services_program"), callback_data="services:program")],
        [
            InlineKeyboardButton(text=texts.get("menu.btn_booking"), callback_data="booking:start"),
            InlineKeyboardButton(text=cart_label,                    callback_data="cart:view"),
        ],
        [InlineKeyboardButton(text=texts.get("menu.btn_info"),    callback_data="info:list")],
        [InlineKeyboardButton(text=texts.get("menu.btn_ai_chat"), callback_data="ai:start")],
    ]
    if _active > 0:
        rows.insert(4, [InlineKeyboardButton(text=bookings_label, callback_data="booking:my")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
