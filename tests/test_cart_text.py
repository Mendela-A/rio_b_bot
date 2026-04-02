"""
Тести для cart_text — відображення кошика (🛒).
Покриває Decimal з asyncpg, price_per_child, порожні ціни, total.
"""
from decimal import Decimal
import pytest

from app.handlers._utils import cart_text


def item(name, *, price=None, price_per_child=None, qty=1):
    return {"name": name, "price": price, "price_per_child": price_per_child, "quantity": qty}


class TestCartText:
    def test_header_present(self):
        text = cart_text([item("Торт", price=300)])
        assert "🛒" in text

    def test_header_shows_count_one(self):
        text = cart_text([item("Торт", price=300)])
        assert "1 послуга" in text

    def test_header_shows_count_two(self):
        text = cart_text([item("Торт", price=300), item("Кульки", price=50)])
        assert "2 послуги" in text

    def test_header_shows_count_five(self):
        items = [item(f"Послуга {i}", price=100) for i in range(5)]
        text = cart_text(items)
        assert "5 послуг" in text

    def test_regular_price(self):
        text = cart_text([item("Торт", price=500, qty=2)])
        assert "Торт" in text
        assert "500" in text
        assert "💰 Разом: 1000" in text

    def test_price_per_child(self):
        text = cart_text([item("VR", price_per_child=150, qty=3)])
        assert "грн/дитина" in text
        assert "150" in text
        assert "💰 Разом: 450" in text

    def test_no_price_no_total(self):
        text = cart_text([item("Включено")])
        assert "Включено" in text
        assert "💰" not in text

    def test_multiple_items_total(self):
        items = [
            item("Торт", price=400, qty=1),
            item("Кульки", price=50, qty=10),
        ]
        text = cart_text(items)
        assert "💰 Разом: 900" in text

    def test_ppc_and_fixed_total(self):
        items = [
            item("VR", price_per_child=100, qty=3),   # 300
            item("Торт", price=200, qty=1),             # 200
        ]
        text = cart_text(items)
        assert "💰 Разом: 500" in text

    # ── Decimal з asyncpg ─────────────────────────────────────────────────────

    def test_decimal_price_no_typeerror(self):
        """asyncpg повертає NUMERIC як Decimal — не кидає TypeError."""
        items = [{"name": "Торт", "price": Decimal("500"), "price_per_child": None, "quantity": 2}]
        text = cart_text(items)
        assert "💰 Разом: 1000" in text

    def test_decimal_ppc_no_typeerror(self):
        items = [{"name": "VR", "price": None, "price_per_child": Decimal("150"), "quantity": 4}]
        text = cart_text(items)
        assert "грн/дитина" in text
        assert "💰 Разом: 600" in text

    def test_decimal_mixed(self):
        """Decimal ppc + Decimal price — обидва рахуються без помилок."""
        items = [
            {"name": "VR", "price": None, "price_per_child": Decimal("200"), "quantity": 2},
            {"name": "Торт", "price": Decimal("300"), "price_per_child": None, "quantity": 1},
        ]
        text = cart_text(items)
        assert "💰 Разом: 700" in text
