"""
Тести для _service_label — відображення ціни у кнопках списку послуг.
Без aiogram — тестуємо чисту логіку через dict замість asyncpg.Record.
"""
import pytest

# Імпортуємо напряму з модуля (aiogram не потрібен для _service_label)
from app.keyboards.services_kb import _service_label


def svc(name, *, price=None, price_per_child=None):
    """Мокує asyncpg.Record як dict."""
    return {"name": name, "price": price, "price_per_child": price_per_child}


class TestServiceLabel:
    def test_only_price(self):
        """Фіксована ціна — показує грн."""
        assert _service_label(svc("Торт", price=500)) == "Торт — 500 грн"

    def test_only_price_per_child(self):
        """Тільки price_per_child — показує грн/дит."""
        assert _service_label(svc("VR", price_per_child=150)) == "VR — 150 грн/дит."

    def test_price_per_child_wins_over_price(self):
        """Якщо є обидва — price_per_child пріоритетніший."""
        label = _service_label(svc("Шоу", price=500, price_per_child=100))
        assert "грн/дит." in label
        assert "100" in label
        assert "500" not in label

    def test_no_price_shows_name_only(self):
        """Без ціни — тільки назва."""
        assert _service_label(svc("Включено")) == "Включено"

    def test_price_zero_shows_name_only(self):
        """price=0 — falsy, тільки назва."""
        assert _service_label(svc("Включено", price=0)) == "Включено"

    def test_price_per_child_zero_falls_back_to_price(self):
        """price_per_child=0 — falsy, показує фіксовану ціну."""
        label = _service_label(svc("Шоу", price=300, price_per_child=0))
        assert "300 грн" in label
        assert "дит." not in label

    def test_decimal_price_rounded(self):
        """Ціна з копійками округляється до цілого."""
        assert _service_label(svc("Послуга", price=199.99)) == "Послуга — 200 грн"

    def test_decimal_ppc_rounded(self):
        assert _service_label(svc("VR", price_per_child=149.5)) == "VR — 150 грн/дит."
