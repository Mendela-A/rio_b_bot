"""Tests for admin notification content — verifies entry_rate and cart_items are shown correctly."""
import pytest


def build_notify_lines(data: dict, cart_items: list, entry_rate: float = 0) -> list[str]:
    """Extracted logic from _notify_admin for unit testing without aiogram/Bot dependency."""
    children_count = data.get("children_count", 0)

    def fmt_date(iso):
        if not iso or len(iso) < 10:
            return "—"
        return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"

    lines = [
        f"📅 Нове бронювання #{data['booking_id']}",
        f"📆 Дата: {fmt_date(data['booking_date'])}",
    ]
    lines.append("\nВартість:")
    total = 0
    if entry_rate and children_count:
        entry_total = entry_rate * children_count
        total += entry_total
        lines.append(f"🎟 Вхід: {entry_rate:.0f} грн × {children_count} дітей = {entry_total:.0f} грн")
    if cart_items:
        for item in cart_items:
            qty = item["quantity"]
            ppc = float(item.get("price_per_child") or 0)
            price = float(item["price"] or 0)
            if ppc:
                subtotal = ppc * qty
                total += subtotal
                lines.append(f"• {item['name']} — {ppc:.0f} грн/дитина × {qty} = {subtotal:.0f} грн")
            elif price:
                total += price * qty
                lines.append(f"• {item['name']} — {price:.0f} грн × {qty}")
            else:
                lines.append(f"• {item['name']} × {qty}")
    if not entry_rate and not cart_items:
        lines.append("Послуги не обрані")
    if total:
        lines.append(f"\n💰 Разом: {total:.0f} грн")
    return lines


def make_data(**kwargs):
    base = {"booking_id": 1, "booking_date": "2026-04-10", "children_count": 3, "full_name": "Тест"}
    return {**base, **kwargs}


def make_item(name="Торт", price=None, price_per_child=None, quantity=1):
    return {"name": name, "price": price, "price_per_child": price_per_child, "quantity": quantity}


class TestNotifyAdminContent:
    def test_entry_rate_shown(self):
        lines = build_notify_lines(make_data(), [], entry_rate=300)
        text = "\n".join(lines)
        assert "🎟 Вхід" in text
        assert "300" in text
        assert "900" in text  # 300 * 3 дітей

    def test_entry_rate_not_shown_when_zero(self):
        lines = build_notify_lines(make_data(), [], entry_rate=0)
        text = "\n".join(lines)
        assert "🎟" not in text
        assert "Послуги не обрані" in text

    def test_cart_item_regular(self):
        lines = build_notify_lines(make_data(), [make_item("Торт", price=500)], entry_rate=0)
        text = "\n".join(lines)
        assert "Торт" in text
        assert "500" in text
        assert "💰 Разом: 500" in text

    def test_cart_item_price_per_child(self):
        lines = build_notify_lines(make_data(), [make_item("Аніматор", price_per_child=150, quantity=4)], entry_rate=0)
        text = "\n".join(lines)
        assert "150" in text and "4" in text
        assert "600" in text  # 150 * 4

    def test_entry_rate_plus_cart_total(self):
        """entry_rate + послуга — total = 300*3 + 500 = 1400."""
        lines = build_notify_lines(
            make_data(children_count=3),
            [make_item("Торт", price=500)],
            entry_rate=300,
        )
        text = "\n".join(lines)
        assert "1400" in text

    def test_no_total_when_no_prices(self):
        """Послуги без цін — рядок '💰 Разом' не з'являється."""
        lines = build_notify_lines(make_data(), [make_item("Включено")], entry_rate=0)
        text = "\n".join(lines)
        assert "💰" not in text

    def test_decimal_ppc_with_float_entry_rate_no_typeerror(self):
        """Реальний кейс: entry_rate=float, ppc=Decimal з БД — TypeError без float()."""
        from decimal import Decimal
        item = make_item("Аніматор", price_per_child=Decimal("150"), quantity=3)
        # entry_rate робить total=float, потім Decimal ppc → TypeError до фіксу
        lines = build_notify_lines(make_data(children_count=3), [item], entry_rate=300.0)
        text = "\n".join(lines)
        assert "150" in text
        assert "1350" in text  # 300*3 + 150*3 = 900 + 450

    def test_decimal_price_with_float_entry_rate_no_typeerror(self):
        """price=Decimal з БД при наявному entry_rate=float."""
        from decimal import Decimal
        item = make_item("Торт", price=Decimal("500"), quantity=1)
        lines = build_notify_lines(make_data(children_count=2), [item], entry_rate=200.0)
        text = "\n".join(lines)
        assert "500" in text
        assert "900" in text  # 200*2 + 500
