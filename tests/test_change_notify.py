"""Tests for _notify_admin_change_request content — price_per_child support."""
import pytest


def build_change_notify_lines(
    booking: dict,
    data: dict,
    proposed_date_str: str,
    proposed_children: int,
    cart_items: list,
) -> list[str]:
    """Extracted logic from _notify_admin_change_request for unit testing."""
    def fmt_date(iso):
        if not iso or len(iso) < 10:
            return "—"
        return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"

    booking_id = booking["id"]
    orig_date_str = data.get("orig_date", "")
    orig_children = data.get("orig_children", "?")
    lines = [
        f"✏️ Запит на зміну бронювання #{booking_id}",
        f"👤 {booking['full_name']}",
        f"📱 {booking['phone']}",
        f"📆 Дата: {fmt_date(orig_date_str)} → {fmt_date(proposed_date_str)}",
        f"👶 Дітей: {orig_children} → {proposed_children}",
    ]
    if cart_items:
        lines.append("\nНові послуги:")
        total = 0
        for item in cart_items:
            qty = item["quantity"]
            ppc = item.get("price_per_child")
            price = item["price"]
            if ppc:
                subtotal = ppc * qty
                total += subtotal
                lines.append(f"• {item['name']} — {ppc:.0f} грн/дитина × {qty} = {subtotal:.0f} грн")
            elif price:
                total += price * qty
                lines.append(f"• {item['name']} — {price:.0f} грн × {qty}")
            else:
                lines.append(f"• {item['name']} × {qty}")
        if total:
            lines.append(f"\n💰 Разом: {total:.0f} грн")
    else:
        lines.append("\nПослуги не обрані")
    return lines


def make_booking(**kwargs):
    base = {"id": 5, "full_name": "Тест Тестів", "phone": "+380991234567"}
    return {**base, **kwargs}


def make_data(**kwargs):
    base = {"orig_date": "2026-04-10", "orig_children": 2}
    return {**base, **kwargs}


def make_item(name="Послуга", *, price=None, price_per_child=None, quantity=1):
    return {"name": name, "price": price, "price_per_child": price_per_child, "quantity": quantity}


class TestChangeNotifyContent:
    def test_header_contains_booking_id(self):
        lines = build_change_notify_lines(make_booking(id=42), make_data(), "2026-05-01", 3, [])
        assert any("42" in l for l in lines)

    def test_date_change_shown(self):
        lines = build_change_notify_lines(
            make_booking(), make_data(orig_date="2026-04-10"), "2026-05-01", 3, []
        )
        text = "\n".join(lines)
        assert "10.04.2026" in text
        assert "01.05.2026" in text

    def test_children_change_shown(self):
        lines = build_change_notify_lines(
            make_booking(), make_data(orig_children=2), "2026-05-01", 4, []
        )
        text = "\n".join(lines)
        assert "2 → 4" in text

    def test_no_services_label(self):
        lines = build_change_notify_lines(make_booking(), make_data(), "2026-05-01", 3, [])
        assert any("Послуги не обрані" in l for l in lines)

    def test_regular_price_item(self):
        items = [make_item("Торт", price=500, quantity=1)]
        lines = build_change_notify_lines(make_booking(), make_data(), "2026-05-01", 3, items)
        text = "\n".join(lines)
        assert "Торт" in text
        assert "500" in text
        assert "💰 Разом: 500" in text

    def test_price_per_child_item(self):
        """ppc item must show грн/дитина format and correct subtotal."""
        items = [make_item("Аніматор", price_per_child=150, quantity=3)]
        lines = build_change_notify_lines(make_booking(), make_data(), "2026-05-01", 3, items)
        text = "\n".join(lines)
        assert "грн/дитина" in text
        assert "150" in text
        assert "450" in text  # 150 × 3
        assert "💰 Разом: 450" in text

    def test_mixed_items_total(self):
        """Regular + ppc: total = 500 + 150×3 = 950."""
        items = [
            make_item("Торт", price=500, quantity=1),
            make_item("Аніматор", price_per_child=150, quantity=3),
        ]
        lines = build_change_notify_lines(make_booking(), make_data(), "2026-05-01", 3, items)
        text = "\n".join(lines)
        assert "950" in text

    def test_free_item_no_total(self):
        """Item without price — no total line."""
        items = [make_item("Включено", price=None, price_per_child=None, quantity=1)]
        lines = build_change_notify_lines(make_booking(), make_data(), "2026-05-01", 3, items)
        text = "\n".join(lines)
        assert "Включено" in text
        assert "💰" not in text

    def test_ppc_not_treated_as_free(self):
        """Bug regression: ppc item must NOT fall into the free/no-price branch."""
        items = [make_item("Шоу", price=None, price_per_child=200, quantity=2)]
        lines = build_change_notify_lines(make_booking(), make_data(), "2026-05-01", 2, items)
        text = "\n".join(lines)
        assert "200" in text
        assert "400" in text  # 200 × 2
        # must NOT show "× 2" without price context (old broken format)
        assert "грн/дитина" in text
