"""Tests for quick booking children count feature.

Covers:
- Admin inquiry notification text with/without children_count
- Validation logic for children count input (1-50)
"""
import pytest


# ─── Helpers (mirror logic from booking.py) ──────────────────────────────────

def build_inquiry_text(inquiry_id, service_name, full_name, phone, children_count=None):
    children_line = f"\n👶 Дітей: {children_count}" if children_count is not None else ""
    return (
        f"⚡ Нова заявка #{inquiry_id}\n"
        f"🎯 {service_name}\n"
        f"👤 {full_name}\n"
        f"📱 {phone}"
        f"{children_line}\n"
        "📞 Менеджер зв'яжеться з вами найближчим часом"
    )


def is_valid_children_input(text: str) -> bool:
    return text.isdigit() and 1 <= int(text) <= 50


# ─── Admin notification text ──────────────────────────────────────────────────

class TestInquiryNotifyText:
    def test_children_line_present(self):
        text = build_inquiry_text(1, "Шоу-програма", "Іван", "+380991234567", children_count=5)
        assert "👶 Дітей: 5" in text

    def test_children_line_absent_when_none(self):
        text = build_inquiry_text(1, "Шоу-програма", "Іван", "+380991234567", children_count=None)
        assert "👶 Дітей" not in text

    def test_base_fields_always_present(self):
        text = build_inquiry_text(42, "Аніматор", "Марія", "+380501112233", children_count=3)
        assert "⚡ Нова заявка #42" in text
        assert "Аніматор" in text
        assert "Марія" in text
        assert "+380501112233" in text

    def test_children_count_one(self):
        text = build_inquiry_text(1, "Послуга", "Тест", "+380", children_count=1)
        assert "👶 Дітей: 1" in text

    def test_children_count_large(self):
        text = build_inquiry_text(1, "Послуга", "Тест", "+380", children_count=50)
        assert "👶 Дітей: 50" in text


# ─── Input validation ─────────────────────────────────────────────────────────

class TestChildrenInputValidation:
    @pytest.mark.parametrize("value", ["1", "25", "50"])
    def test_valid_range(self, value):
        assert is_valid_children_input(value) is True

    def test_zero_invalid(self):
        assert is_valid_children_input("0") is False

    def test_51_invalid(self):
        assert is_valid_children_input("51") is False

    @pytest.mark.parametrize("value", ["abc", "", "1.5", " "])
    def test_non_digit_invalid(self, value):
        assert is_valid_children_input(value) is False

    def test_negative_invalid(self):
        # "-1".isdigit() == False
        assert is_valid_children_input("-1") is False
