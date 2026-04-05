"""
Тести для _state_flags(), _empty_cart_kb() з cart.py
та confirm_booking_kb() з keyboards/booking_kb.py.
"""
import pytest
from app.handlers.cart import _state_flags, _empty_cart_kb
from app.keyboards.booking_kb import confirm_booking_kb


class TestStateFlags:
    def test_none_state(self):
        assert _state_flags(None) == (False, False)

    def test_booking_state(self):
        in_booking, in_change = _state_flags("BookingStates:waiting_date")
        assert in_booking is True
        assert in_change is False

    def test_change_state(self):
        in_booking, in_change = _state_flags("ChangeStates:waiting_date")
        assert in_booking is False
        assert in_change is True

    def test_cart_state_neither(self):
        in_booking, in_change = _state_flags("CartStates:waiting_service_quantity")
        assert in_booking is False
        assert in_change is False

    def test_empty_string(self):
        assert _state_flags("") == (False, False)

    def test_booking_confirm_state(self):
        in_booking, in_change = _state_flags("BookingStates:confirming")
        assert in_booking is True
        assert in_change is False

    def test_change_confirming_state(self):
        in_booking, in_change = _state_flags("ChangeStates:confirming")
        assert in_booking is False
        assert in_change is True


class TestEmptyCartKb:
    def _button_texts(self, kb):
        return [btn.text for row in kb.inline_keyboard for btn in row]

    def _callback_datas(self, kb):
        return [btn.callback_data for row in kb.inline_keyboard for btn in row]

    def test_default_state_shows_services(self):
        kb = _empty_cart_kb(in_booking=False, in_change=False)
        texts = self._button_texts(kb)
        assert any("Переглянути послуги" in t or "Програми" in t for t in texts)
        assert not any("підтвердження" in t for t in texts)

    def test_booking_state_shows_back_to_confirm(self):
        kb = _empty_cart_kb(in_booking=True, in_change=False)
        datas = self._callback_datas(kb)
        assert "booking:resume_confirm" in datas

    def test_booking_state_shows_add_service(self):
        kb = _empty_cart_kb(in_booking=True, in_change=False)
        datas = self._callback_datas(kb)
        assert "booking:add_service" in datas

    def test_change_state_shows_back_to_changes(self):
        kb = _empty_cart_kb(in_booking=False, in_change=True)
        datas = self._callback_datas(kb)
        assert "change:resume_confirm" in datas

    def test_change_state_no_booking_buttons(self):
        kb = _empty_cart_kb(in_booking=False, in_change=True)
        datas = self._callback_datas(kb)
        assert "booking:resume_confirm" not in datas
        assert "booking:add_service" not in datas

    def test_all_states_have_main_menu(self):
        for in_booking, in_change in [(False, False), (True, False), (False, True)]:
            kb = _empty_cart_kb(in_booking=in_booking, in_change=in_change)
            datas = self._callback_datas(kb)
            assert "main_menu" in datas


class TestConfirmBookingKb:
    def _cart_button_text(self, kb):
        for row in kb.inline_keyboard:
            for btn in row:
                if "cart" in btn.callback_data or "кошик" in btn.text.lower():
                    return btn.text
        return None

    def test_no_items_shows_empty(self):
        kb = confirm_booking_kb(cart_items=None)
        text = self._cart_button_text(kb)
        assert text == "🛒 Кошик порожній"

    def test_empty_list_shows_empty(self):
        kb = confirm_booking_kb(cart_items=[])
        text = self._cart_button_text(kb)
        assert text == "🛒 Кошик порожній"

    def test_one_item_shows_count(self):
        kb = confirm_booking_kb(cart_items=[{"name": "Торт"}])
        text = self._cart_button_text(kb)
        assert "(1)" in text

    def test_three_items_shows_count(self):
        items = [{"name": f"Послуга {i}"} for i in range(3)]
        kb = confirm_booking_kb(cart_items=items)
        text = self._cart_button_text(kb)
        assert "(3)" in text

    def test_confirm_button_always_present(self):
        kb = confirm_booking_kb(cart_items=None)
        datas = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "booking:confirm" in datas

    def test_cart_callback_data_unchanged(self):
        kb = confirm_booking_kb(cart_items=[{"name": "Торт"}])
        for row in kb.inline_keyboard:
            for btn in row:
                if "(1)" in btn.text:
                    assert btn.callback_data == "booking:view_cart"


class TestMainMenuKb:
    from app.keyboards.main_menu import main_menu_kb

    def _cart_btn(self, kb):
        for row in kb.inline_keyboard:
            for btn in row:
                if btn.callback_data == "cart:view":
                    return btn.text
        return None

    def test_no_count_default(self):
        from app.keyboards.main_menu import main_menu_kb
        kb = main_menu_kb()
        text = self._cart_btn(kb)
        assert "(" not in text

    def test_zero_count_no_badge(self):
        from app.keyboards.main_menu import main_menu_kb
        kb = main_menu_kb(cart_count=0)
        text = self._cart_btn(kb)
        assert "(" not in text

    def test_count_shown(self):
        from app.keyboards.main_menu import main_menu_kb
        kb = main_menu_kb(cart_count=3)
        text = self._cart_btn(kb)
        assert "(3)" in text

    def test_cart_callback_unchanged(self):
        from app.keyboards.main_menu import main_menu_kb
        kb = main_menu_kb(cart_count=5)
        for row in kb.inline_keyboard:
            for btn in row:
                if "(5)" in btn.text:
                    assert btn.callback_data == "cart:view"

    def _my_bookings_btn(self, kb):
        for row in kb.inline_keyboard:
            for btn in row:
                if btn.callback_data == "booking:my":
                    return btn
        return None

    def test_my_bookings_hidden_by_default(self):
        from app.keyboards.main_menu import main_menu_kb
        kb = main_menu_kb()
        assert self._my_bookings_btn(kb) is None

    def test_my_bookings_hidden_when_false(self):
        from app.keyboards.main_menu import main_menu_kb
        kb = main_menu_kb(has_bookings=False)
        assert self._my_bookings_btn(kb) is None

    def test_my_bookings_shown_when_true(self):
        from app.keyboards.main_menu import main_menu_kb
        kb = main_menu_kb(has_bookings=True)
        assert self._my_bookings_btn(kb) is not None

    def test_my_bookings_position(self):
        """Кнопка 'Мої бронювання' стоїть після кошику, перед інфо."""
        from app.keyboards.main_menu import main_menu_kb
        kb = main_menu_kb(has_bookings=True)
        callbacks = [row[0].callback_data for row in kb.inline_keyboard]
        my_idx = callbacks.index("booking:my")
        # cart row has two buttons — find the row index with cart:view
        cart_row_idx = next(
            i for i, row in enumerate(kb.inline_keyboard)
            if any(b.callback_data == "cart:view" for b in row)
        )
        info_idx = callbacks.index("info:list")
        assert cart_row_idx < my_idx < info_idx

    def test_other_buttons_present_regardless(self):
        from app.keyboards.main_menu import main_menu_kb
        expected = {"services:venue", "services:offsite", "services:program",
                    "booking:start", "cart:view", "info:list", "ai:start"}
        for has_bkn in (False, True):
            kb = main_menu_kb(has_bookings=has_bkn)
            found = {btn.callback_data for row in kb.inline_keyboard for btn in row}
            assert expected.issubset(found)
