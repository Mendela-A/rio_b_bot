"""
Тести для price_per_child — охоплює edge cases у services_lines та _float_or_none.
Без aiogram/asyncpg/starlette — чисті функції.
"""
import pytest

from app.handlers._utils import services_lines


# ─── Хелпер ──────────────────────────────────────────────────────────────────

def item(name, *, price=None, price_per_child=None, qty=1):
    return {"name": name, "price": price, "price_per_child": price_per_child, "quantity": qty}


# ─── _float_or_none (admin helper) ───────────────────────────────────────────
# Дублюємо логіку тут, бо admin/views/services_editor.py тягне starlette
# Еталон: admin/views/services_editor.py:136

def _float_or_none(value):
    try:
        v = float(value)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


class TestFloatOrNone:
    def test_valid_positive(self):
        assert _float_or_none("150") == 150.0

    def test_valid_decimal(self):
        assert _float_or_none("99.90") == 99.9

    def test_zero_returns_none(self):
        assert _float_or_none("0") is None

    def test_negative_returns_none(self):
        assert _float_or_none("-50") is None

    def test_none_returns_none(self):
        assert _float_or_none(None) is None

    def test_empty_string_returns_none(self):
        assert _float_or_none("") is None

    def test_non_numeric_returns_none(self):
        assert _float_or_none("abc") is None

    def test_integer_input(self):
        assert _float_or_none(200) == 200.0


# ─── services_lines: price_per_child пріоритет ───────────────────────────────

class TestPricePerChildPriority:
    def test_ppc_wins_over_price(self):
        """Якщо є і price і price_per_child — відображається грн/дитина."""
        items = [item("Шоу", price=500, price_per_child=100, qty=3)]
        lines = services_lines(items)
        text = "\n".join(lines)
        assert "грн/дитина" in text
        assert "300" in text   # 100 × 3 = 300, не 500

    def test_ppc_zero_falls_back_to_price(self):
        """price_per_child=0 — falsy, відображає фіксовану price."""
        items = [item("Шоу", price=500, price_per_child=0, qty=1)]
        lines = services_lines(items)
        text = "\n".join(lines)
        assert "грн/дитина" not in text
        assert "500" in text

    def test_ppc_none_falls_back_to_price(self):
        """price_per_child=None — відображає фіксовану price."""
        items = [item("Торт", price=300, price_per_child=None, qty=2)]
        lines = services_lines(items)
        text = "\n".join(lines)
        assert "грн/дитина" not in text
        assert "300" in text


# ─── services_lines: кілька items з ppc ──────────────────────────────────────

class TestMultiplePpcItems:
    def test_two_ppc_items_total(self):
        """Два items з price_per_child — total = сума обох subtotals."""
        items = [
            item("Аніматор", price_per_child=100, qty=2),   # 200
            item("Шоу-програма", price_per_child=150, qty=3),  # 450
        ]
        lines = services_lines(items)
        text = "\n".join(lines)
        assert "💰 Разом: 650" in text

    def test_ppc_and_fixed_total(self):
        """Змішаний кошик: ppc + фіксована ціна — total враховує обидва."""
        items = [
            item("Аніматор", price_per_child=100, qty=2),  # 200
            item("Торт", price=400, qty=1),                 # 400
        ]
        lines = services_lines(items)
        text = "\n".join(lines)
        assert "💰 Разом: 600" in text

    def test_ppc_with_entry_rate_total(self):
        """ppc + entry_rate — обидва в total."""
        items = [item("Шоу", price_per_child=150, qty=3)]  # 450
        lines = services_lines(items, entry_rate=200, children_count=3)  # 600
        text = "\n".join(lines)
        assert "💰 Разом: 1050" in text


# ─── Формат рядка price_per_child ────────────────────────────────────────────

class TestPpcLineFormat:
    def test_format_contains_multiplier(self):
        """Рядок містить '× qty = subtotal'."""
        items = [item("Аніматор", price_per_child=200, qty=4)]
        lines = services_lines(items)
        assert any("200" in l and "4" in l and "800" in l for l in lines)

    def test_label_грн_дитина(self):
        items = [item("Шоу", price_per_child=75, qty=5)]
        lines = services_lines(items)
        assert any("грн/дитина" in l for l in lines)
