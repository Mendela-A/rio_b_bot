"""
Тести для _state_flags() та _empty_cart_kb() з cart.py.

_state_flags() — чиста функція: визначає чи юзер у BookingStates / ChangeStates
_empty_cart_kb() — чиста функція: повертає правильну клавіатуру залежно від стану
"""
import pytest
from app.handlers.cart import _state_flags, _empty_cart_kb


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
