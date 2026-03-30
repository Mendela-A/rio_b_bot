"""Unit tests for _utils helpers."""
import pytest

from app.handlers._utils import fmt_date, PHONE_RE


class TestFmtDate:
    def test_valid_iso(self):
        assert fmt_date("2026-03-30") == "30.03.2026"

    def test_empty_string(self):
        assert fmt_date("") == "—"

    def test_none(self):
        assert fmt_date(None) == "—"

    def test_short_string(self):
        assert fmt_date("2026") == "—"


class TestPhoneRe:
    def test_valid_ukrainian(self):
        assert PHONE_RE.match("+380991234567")

    def test_valid_with_spaces(self):
        assert PHONE_RE.match("+38 (099) 123-45-67")

    def test_too_short(self):
        assert not PHONE_RE.match("123")

    def test_letters_rejected(self):
        assert not PHONE_RE.match("abc1234567")
