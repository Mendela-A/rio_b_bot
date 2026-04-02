"""
Тести для логіки зміни бронювання.

Покриває:
- Фільтрацію entry fee при відновленні кошика (service_id IS NULL пропускається)
- _change_confirm_text(): текст підтвердження запиту на зміну
"""
import pytest
from decimal import Decimal
from app.handlers.booking import _change_confirm_text


# ── Хелпери ──────────────────────────────────────────────────────────────────

def booking_item(service_id, name, price=None, price_per_child=None, quantity=1):
    """Імітує рядок asyncpg з booking_items."""
    return {
        "service_id": service_id,
        "name": name,
        "price": price,
        "price_per_child": price_per_child,
        "quantity": quantity,
    }


def cart_item(name, price=None, price_per_child=None, quantity=1):
    return {
        "name": name,
        "price": price,
        "price_per_child": price_per_child,
        "quantity": quantity,
    }


# ── Фільтрація entry fee при відновленні кошика ───────────────────────────────

class TestEntryFeeFilter:
    """
    При change_booking_start кошик заповнюється з booking_items,
    але рядки з service_id=None (entry fee) мають пропускатися.
    """

    def _filter(self, items):
        """Реплікує логіку з change_booking_start."""
        return [item for item in items if item["service_id"] is not None]

    def test_entry_fee_excluded(self):
        items = [
            booking_item(None, "Вхід (будні)", price=Decimal("200")),
            booking_item(5, "Аніматор", price=Decimal("500")),
        ]
        result = self._filter(items)
        assert len(result) == 1
        assert result[0]["service_id"] == 5

    def test_all_real_services_kept(self):
        items = [
            booking_item(1, "Торт", price=Decimal("300")),
            booking_item(2, "Кульки", price=Decimal("100")),
            booking_item(3, "VR", price_per_child=Decimal("150"), quantity=4),
        ]
        result = self._filter(items)
        assert len(result) == 3

    def test_empty_booking_items(self):
        assert self._filter([]) == []

    def test_only_entry_fee_returns_empty(self):
        items = [booking_item(None, "Вхід (вихідні)", price=Decimal("300"))]
        assert self._filter(items) == []

    def test_multiple_entry_fees_excluded(self):
        """На випадок якщо якось опинилось кілька entry fee рядків."""
        items = [
            booking_item(None, "Вхід (будні)", price=Decimal("200")),
            booking_item(None, "Вхід (вихідні)", price=Decimal("300")),
            booking_item(7, "Фотозона", price=Decimal("400")),
        ]
        result = self._filter(items)
        assert len(result) == 1
        assert result[0]["name"] == "Фотозона"


# ── _change_confirm_text ──────────────────────────────────────────────────────

class TestChangeConfirmText:
    def _data(self, booking_id=42, orig_date="2025-06-10", proposed_date="2025-06-15",
              orig_children=3):
        return {
            "booking_id": booking_id,
            "orig_date": orig_date,
            "proposed_date": proposed_date,
            "orig_children": orig_children,
        }

    def test_contains_booking_id(self):
        text = _change_confirm_text(self._data(booking_id=99), 4, [])
        assert "#99" in text

    def test_shows_date_change(self):
        text = _change_confirm_text(self._data(orig_date="2025-06-10", proposed_date="2025-06-15"), 4, [])
        assert "→" in text
        # обидві дати присутні
        assert "10" in text
        assert "15" in text

    def test_shows_children_change(self):
        text = _change_confirm_text(self._data(orig_children=3), proposed_children=5, cart_items=[])
        assert "3" in text
        assert "5" in text
        assert "→" in text

    def test_contains_submit_prompt(self):
        text = _change_confirm_text(self._data(), 2, [])
        assert "Надіслати запит" in text

    def test_cart_items_included(self):
        items = [cart_item("Аніматор", price=Decimal("500"))]
        text = _change_confirm_text(self._data(), 3, items)
        assert "Аніматор" in text
        assert "500" in text

    def test_empty_cart_no_crash(self):
        text = _change_confirm_text(self._data(), 2, [])
        assert "Запит на зміну" in text

    def test_ppc_item_in_change_confirm(self):
        items = [cart_item("VR", price_per_child=Decimal("150"), quantity=3)]
        text = _change_confirm_text(self._data(), 3, items)
        assert "VR" in text
        assert "150" in text
