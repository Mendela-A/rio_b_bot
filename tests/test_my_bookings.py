"""Tests for _my_bookings_text and _booking_items_lines."""
from datetime import date, timedelta
from decimal import Decimal


# ── helpers mirroring booking.py logic ──────────────────────────────────────

_STATUS_LABELS = {
    "new":       "🔵 Нове",
    "confirmed": "✅ Підтверджено",
    "cancelled": "⛔ Скасовано",
}


def _booking_items_lines(items: list) -> tuple[list, float]:
    lines = []
    total = 0.0
    for item in items:
        name = item["name"]
        price = float(item["price"] or 0)
        qty = item["quantity"]
        ppc = item.get("price_per_child")

        if item["service_id"] is None:
            lines.append(f"🎟 {name} — {price:.0f} грн")
            total += price
        elif ppc:
            ppc_f = float(ppc)
            lines.append(f"• {name} — {ppc_f:.0f} грн/дитина × {qty} = {price:.0f} грн")
            total += price
        elif price:
            if qty > 1:
                subtotal = price * qty
                lines.append(f"• {name} — {price:.0f} грн × {qty} = {subtotal:.0f} грн")
                total += subtotal
            else:
                lines.append(f"• {name} — {price:.0f} грн")
                total += price
        else:
            lines.append(f"• {name}")
    return lines, total


def _my_bookings_text(bookings: list, items_by_id: dict | None = None) -> str:
    if not bookings:
        return "📋 У вас ще немає бронювань."
    if items_by_id is None:
        items_by_id = {}
    lines = ["📋 <b>Ваші бронювання:</b>\n"]
    for b in bookings:
        date_str = b["booking_date"].strftime("%d.%m.%Y")
        is_past = b["booking_date"] < date.today()
        if is_past and b["status"] in ("new", "confirmed"):
            status = "✔️ Відбулось"
        else:
            status = _STATUS_LABELS.get(b["status"], b["status"])
        lines.append(f"<b>#{b['id']}</b>  📅 {date_str}  {status}")
        lines.append(f"👶 Дітей: {b['children_count']}")
        adults = b.get("adults_count") or 0
        if adults:
            lines.append(f"👨 Дорослих: {adults}")
        birthday_name = b.get("birthday_person_name") or ""
        if birthday_name:
            bday_date = b.get("birthday_person_date")
            bday_str = bday_date.strftime("%d.%m.%Y") if bday_date else ""
            lines.append(f"🎂 Іменинник: {birthday_name}" + (f" ({bday_str})" if bday_str else ""))
        booking_items = items_by_id.get(b["id"], [])
        if booking_items:
            item_lines, total = _booking_items_lines(booking_items)
            lines.extend(item_lines)
            if total:
                lines.append(f"💰 Разом: {total:.0f} грн")
        else:
            lines.append("🗂 Послуги не обрані")
        lines.append("")
    return "\n".join(lines).strip()


def make_booking(**kwargs):
    base = {
        "id": 1,
        "booking_date": date(2026, 4, 10),
        "status": "new",
        "children_count": 2,
        "adults_count": 0,
        "birthday_person_name": "",
        "birthday_person_date": None,
    }
    return {**base, **kwargs}


def make_item(name, *, service_id=1, price=None, price_per_child=None, quantity=1):
    return {"name": name, "service_id": service_id, "price": price,
            "price_per_child": price_per_child, "quantity": quantity}


def make_entry(price, children):
    return {"name": "Вхід (будні)", "service_id": None, "price": price,
            "price_per_child": None, "quantity": children}


# ── _booking_items_lines ─────────────────────────────────────────────────────

class TestBookingItemsLines:
    def test_entry_fee_icon(self):
        lines, total = _booking_items_lines([make_entry(600, 2)])
        assert any("🎟" in l for l in lines)
        assert total == 600

    def test_entry_fee_label(self):
        lines, _ = _booking_items_lines([make_entry(600, 2)])
        assert any("Вхід (будні)" in l and "600" in l for l in lines)

    def test_fixed_price_qty1(self):
        lines, total = _booking_items_lines([make_item("Торт", price=500)])
        assert any("Торт" in l and "500" in l for l in lines)
        assert total == 500

    def test_fixed_price_qty_gt1(self):
        lines, total = _booking_items_lines([make_item("Кульки", price=50, quantity=10)])
        assert any("50" in l and "10" in l and "500" in l for l in lines)
        assert total == 500

    def test_ppc_item(self):
        lines, total = _booking_items_lines([make_item("Аніматор", price=450, price_per_child=150, quantity=3)])
        assert any("грн/дитина" in l for l in lines)
        assert any("150" in l and "3" in l and "450" in l for l in lines)
        assert total == 450

    def test_no_price_item(self):
        lines, total = _booking_items_lines([make_item("Включено")])
        assert any("Включено" in l for l in lines)
        assert total == 0

    def test_decimal_price_no_typeerror(self):
        lines, total = _booking_items_lines([make_item("Торт", price=Decimal("500"))])
        assert total == 500.0

    def test_decimal_ppc_no_typeerror(self):
        lines, total = _booking_items_lines([
            make_entry(300, 2),
            make_item("Аніматор", price=Decimal("450"), price_per_child=Decimal("150"), quantity=3),
        ])
        assert total == 750.0  # 300 + 450

    def test_total_multiple_items(self):
        items = [
            make_entry(600, 2),
            make_item("Торт", price=500),
            make_item("Аніматор", price=450, price_per_child=150, quantity=3),
        ]
        _, total = _booking_items_lines(items)
        assert total == 1550.0  # 600 + 500 + 450


# ── _my_bookings_text ────────────────────────────────────────────────────────

class TestMyBookingsText:
    def test_empty_list(self):
        assert _my_bookings_text([]) == "📋 У вас ще немає бронювань."

    def test_no_items_shows_placeholder(self):
        text = _my_bookings_text([make_booking()])
        assert "Послуги не обрані" in text

    def test_booking_id_and_date(self):
        text = _my_bookings_text([make_booking(id=19, booking_date=date(2026, 5, 1))])
        assert "#19" in text
        assert "01.05.2026" in text

    def test_status_new(self):
        assert "🔵 Нове" in _my_bookings_text([make_booking(status="new")])

    def test_status_confirmed(self):
        assert "✅ Підтверджено" in _my_bookings_text([make_booking(status="confirmed")])

    def test_status_cancelled(self):
        assert "⛔ Скасовано" in _my_bookings_text([make_booking(status="cancelled")])

    def test_children_count(self):
        assert "Дітей: 3" in _my_bookings_text([make_booking(children_count=3)])

    def test_adults_shown(self):
        assert "Дорослих: 2" in _my_bookings_text([make_booking(adults_count=2)])

    def test_adults_hidden_when_zero(self):
        assert "Дорослих" not in _my_bookings_text([make_booking(adults_count=0)])

    def test_birthday_shown(self):
        text = _my_bookings_text([make_booking(
            birthday_person_name="Аня", birthday_person_date=date(2020, 6, 15)
        )])
        assert "Аня" in text and "15.06.2020" in text

    def test_birthday_without_date(self):
        text = _my_bookings_text([make_booking(birthday_person_name="Аня", birthday_person_date=None)])
        assert "Аня" in text and "None" not in text

    def test_birthday_empty_hidden(self):
        assert "Іменинник" not in _my_bookings_text([make_booking(birthday_person_name="")])

    def test_entry_fee_shown_with_icon(self):
        items_by_id = {1: [make_entry(600, 2)]}
        text = _my_bookings_text([make_booking(id=1)], items_by_id)
        assert "🎟" in text and "600" in text

    def test_fixed_service_shown(self):
        items_by_id = {1: [make_item("Торт", price=500)]}
        text = _my_bookings_text([make_booking(id=1)], items_by_id)
        assert "Торт" in text and "500" in text

    def test_ppc_service_shown(self):
        items_by_id = {1: [make_item("Аніматор", price=450, price_per_child=150, quantity=3)]}
        text = _my_bookings_text([make_booking(id=1)], items_by_id)
        assert "грн/дитина" in text

    def test_total_shown(self):
        items_by_id = {1: [make_entry(600, 2), make_item("Торт", price=500)]}
        text = _my_bookings_text([make_booking(id=1)], items_by_id)
        assert "💰 Разом: 1100" in text

    def test_total_hidden_when_zero(self):
        items_by_id = {1: [make_item("Включено")]}
        text = _my_bookings_text([make_booking(id=1)], items_by_id)
        assert "💰" not in text

    def test_multiple_bookings(self):
        bookings = [make_booking(id=10), make_booking(id=11)]
        text = _my_bookings_text(bookings)
        assert "#10" in text and "#11" in text

    def test_items_per_booking_isolated(self):
        """Items for booking 10 must not appear under booking 11."""
        bookings = [make_booking(id=10), make_booking(id=11)]
        items_by_id = {10: [make_item("Торт", price=500)]}
        text = _my_bookings_text(bookings, items_by_id)
        assert "Торт" in text
        # booking 11 has no items → placeholder
        lines = text.split("\n")
        idx_11 = next(i for i, l in enumerate(lines) if "#11" in l)
        assert any("Послуги не обрані" in l for l in lines[idx_11:])


class TestPastBookingLabel:
    def test_past_confirmed_shows_vidbulos(self):
        past = date.today() - timedelta(days=1)
        text = _my_bookings_text([make_booking(booking_date=past, status="confirmed")])
        assert "✔️ Відбулось" in text
        assert "✅ Підтверджено" not in text

    def test_past_new_shows_vidbulos(self):
        past = date.today() - timedelta(days=1)
        text = _my_bookings_text([make_booking(booking_date=past, status="new")])
        assert "✔️ Відбулось" in text

    def test_past_cancelled_keeps_cancelled_label(self):
        past = date.today() - timedelta(days=1)
        text = _my_bookings_text([make_booking(booking_date=past, status="cancelled")])
        assert "⛔ Скасовано" in text
        assert "✔️ Відбулось" not in text

    def test_future_confirmed_keeps_confirmed_label(self):
        future = date.today() + timedelta(days=1)
        text = _my_bookings_text([make_booking(booking_date=future, status="confirmed")])
        assert "✅ Підтверджено" in text
        assert "✔️ Відбулось" not in text

    def test_today_is_not_past(self):
        today = date.today()
        text = _my_bookings_text([make_booking(booking_date=today, status="confirmed")])
        assert "✅ Підтверджено" in text
        assert "✔️ Відбулось" not in text
