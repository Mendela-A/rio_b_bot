"""
End-to-end сценарії бронювань через confirmation_text / services_lines.
Без aiogram і asyncpg — чисті функції, запускаються локально.

Сценарії відповідають реальним варіантам оформлення в боті.
"""
import pytest

# Імпортуємо напряму, щоб не тягнути aiogram
from app.handlers._utils import confirmation_text, services_lines


# ─── Хелпери ─────────────────────────────────────────────────────────────────

def booking(
    *,
    children_count=3,
    adults_count=1,
    birthday_name="Олексій",
    birthday_date="2019-06-10",
    booking_date="2026-04-10",  # п'ятниця (будній)
    full_name="Марія Коваль",
    phone="+380991234567",
):
    return {
        "full_name": full_name,
        "phone": phone,
        "children_count": children_count,
        "adults_count": adults_count,
        "birthday_person_name": birthday_name,
        "birthday_person_date": birthday_date,
        "booking_date": booking_date,
    }


def item(name, *, price=None, price_per_child=None, qty=1):
    return {"name": name, "price": price, "price_per_child": price_per_child, "quantity": qty}


# ─── Сценарій 1: Мінімальне — тільки тариф входу (будній) ────────────────────

class TestMinimalWeekday:
    """3 дитини, тариф 300 грн, послуги не обрані."""

    def test_entry_line_present(self):
        text = confirmation_text(booking(), [], entry_rate=300)
        assert "🎟" in text
        assert "300" in text

    def test_total_correct(self):
        # 300 × 3 = 900
        text = confirmation_text(booking(), [], entry_rate=300)
        assert "900" in text

    def test_no_services_line(self):
        text = confirmation_text(booking(), [], entry_rate=300)
        assert "Послуги не обрані" not in text


# ─── Сценарій 2: Тільки тариф входу (вихідний — вища ціна) ──────────────────

class TestMinimalWeekend:
    """Субота, тариф 450 грн."""

    def test_higher_rate_shown(self):
        text = confirmation_text(booking(booking_date="2026-04-11"), [], entry_rate=450)
        assert "450" in text

    def test_total_weekend(self):
        # 450 × 3 = 1350
        text = confirmation_text(booking(booking_date="2026-04-11"), [], entry_rate=450)
        assert "1350" in text


# ─── Сценарій 3: Тільки послуги, без тарифу входу ───────────────────────────

class TestServicesOnly:
    """Аніматор на виїзд — тариф входу = 0."""

    def test_service_shown(self):
        items = [item("Аніматор на 2 год.", price=1200)]
        text = confirmation_text(booking(), items, entry_rate=0)
        assert "Аніматор" in text
        assert "1200" in text

    def test_no_entry_tariff_line(self):
        items = [item("Аніматор на 2 год.", price=1200)]
        text = confirmation_text(booking(), items, entry_rate=0)
        assert "🎟" not in text

    def test_total_correct(self):
        items = [item("Аніматор на 2 год.", price=1200)]
        text = confirmation_text(booking(), items, entry_rate=0)
        assert "1200" in text  # total = 1200


# ─── Сценарій 4: Послуга з price_per_child ───────────────────────────────────

class TestPricePerChild:
    """Програма з ціною за дитину: 150 грн × 3 дітей."""

    def test_per_child_label(self):
        items = [item("Шоу-програма", price_per_child=150, qty=3)]
        text = confirmation_text(booking(children_count=3), items)
        assert "грн/дитина" in text
        assert "150" in text
        assert "3" in text

    def test_subtotal(self):
        # 150 × 3 = 450
        items = [item("Шоу-програма", price_per_child=150, qty=3)]
        text = confirmation_text(booking(children_count=3), items)
        assert "450" in text

    def test_total_equals_subtotal(self):
        items = [item("Шоу-програма", price_per_child=150, qty=3)]
        text = confirmation_text(booking(children_count=3), items)
        assert "💰 Разом: 450" in text


# ─── Сценарій 5: Повне — вхід + фікс + price_per_child ───────────────────────

class TestFullBooking:
    """
    Вхід (будні): 300 × 3 = 900
    Торт: 500 × 1 = 500
    Шоу-програма: 150 × 3 = 450
    Total: 1850
    """

    def _make(self):
        items = [
            item("Торт", price=500),
            item("Шоу-програма", price_per_child=150, qty=3),
        ]
        return confirmation_text(booking(children_count=3), items, entry_rate=300)

    def test_all_three_components(self):
        text = self._make()
        assert "🎟" in text       # вхід
        assert "Торт" in text
        assert "Шоу-програма" in text

    def test_total(self):
        text = self._make()
        assert "1850" in text

    def test_booking_date_formatted(self):
        text = self._make()
        assert "10.04.2026" in text


# ─── Сценарій 6: Без іменинника ──────────────────────────────────────────────

class TestNobirthday:
    def test_no_none_literal(self):
        data = booking(birthday_name=None, birthday_date=None)
        text = confirmation_text(data, [])
        assert "None" not in text

    def test_dash_shown(self):
        data = booking(birthday_name=None, birthday_date=None)
        text = confirmation_text(data, [])
        assert "Іменинник: —" in text

    def test_name_without_date(self):
        """Ім'я є, але дата дня народження не вказана."""
        data = booking(birthday_name="Аня", birthday_date=None)
        text = confirmation_text(data, [])
        assert "Аня" in text
        assert "None" not in text


# ─── Сценарій 7: Без дорослих ────────────────────────────────────────────────

class TestNoAdults:
    def test_dash_for_zero(self):
        data = booking(adults_count=0)
        text = confirmation_text(data, [])
        # adults_count=0 — falsy, показується як "0" або "—" — перевіряємо що немає None
        assert "None" not in text

    def test_adults_count_present(self):
        data = booking(adults_count=2)
        text = confirmation_text(data, [])
        assert "2" in text


# ─── Сценарій 8: Кілька однакових послуг (quantity > 1) ─────────────────────

class TestMultipleQuantity:
    def test_quantity_in_line(self):
        items = [item("Кульки", price=50, qty=10)]
        text = confirmation_text(booking(), items)
        assert "50" in text
        assert "10" in text

    def test_total_multiplied(self):
        # 50 × 10 = 500
        items = [item("Кульки", price=50, qty=10)]
        text = confirmation_text(booking(), items)
        assert "500" in text


# ─── Сценарій 9: Безкоштовна послуга (price=None) ────────────────────────────

class TestFreeService:
    def test_shown_without_price(self):
        items = [item("Привітання від аніматора")]  # price=None
        text = confirmation_text(booking(), items)
        assert "Привітання" in text

    def test_no_total_shown(self):
        items = [item("Привітання від аніматора")]
        text = confirmation_text(booking(), items)
        assert "💰" not in text


# ─── Сценарій 10: Порожнє замовлення без тарифу ─────────────────────────────

class TestEmptyBooking:
    def test_no_services_message(self):
        text = confirmation_text(booking(), [], entry_rate=0)
        assert "Послуги не обрані" in text

    def test_no_total_shown(self):
        text = confirmation_text(booking(), [], entry_rate=0)
        assert "💰" not in text
