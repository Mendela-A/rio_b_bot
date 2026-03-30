"""Unit tests for confirmation_text and services_lines — no DB required."""
import pytest

from app.handlers._utils import services_lines, confirmation_text


def make_item(name="Аніматор", price=None, price_per_child=None, quantity=1):
    return {"name": name, "price": price, "price_per_child": price_per_child, "quantity": quantity}


class TestServicesLines:
    def test_empty_cart_no_tariff(self):
        lines = services_lines([], entry_rate=0, children_count=0)
        assert lines == ["\nПослуги не обрані"]

    def test_regular_service(self):
        items = [make_item("Торт", price=300, quantity=1)]
        lines = services_lines(items)
        assert any("Торт" in l for l in lines)
        assert any("300" in l for l in lines)

    def test_price_per_child_service(self):
        items = [make_item("Аніматор", price_per_child=150, quantity=4)]
        lines = services_lines(items)
        assert any("150" in l and "4" in l for l in lines)
        assert any("600" in l for l in lines)  # 150 * 4 = 600

    def test_entry_tariff_in_total(self):
        lines = services_lines([], entry_rate=200, children_count=3)
        assert any("200" in l for l in lines)
        assert any("600" in l for l in lines)  # 200 * 3

    def test_total_shown(self):
        items = [make_item("Послуга", price=500, quantity=2)]
        lines = services_lines(items)
        assert any("1000" in l for l in lines)  # 500 * 2


class TestConfirmationText:
    def _make_data(self):
        return {
            "full_name": "Тест Тестович",
            "phone": "+380991234567",
            "children_count": 2,
            "adults_count": 1,
            "birthday_person_name": "Михайло",
            "birthday_person_date": "2020-05-15",
            "booking_date": "2026-04-10",
        }

    def test_contains_name(self):
        text = confirmation_text(self._make_data(), [])
        assert "Тест Тестович" in text

    def test_contains_date_formatted(self):
        text = confirmation_text(self._make_data(), [])
        assert "10.04.2026" in text

    def test_contains_birthday_formatted(self):
        text = confirmation_text(self._make_data(), [])
        assert "15.05.2020" in text

    def test_contains_services(self):
        items = [make_item("Торт", price=200, quantity=1)]
        text = confirmation_text(self._make_data(), items)
        assert "Торт" in text
        assert "200" in text

    def test_missing_birthday_date(self):
        data = self._make_data()
        data["birthday_person_date"] = None
        text = confirmation_text(data, [])
        assert "Михайло" in text
        assert "None" not in text
