"""Unit tests for pricing logic — no DB required."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.queries.bookings import _resolve_item_price


def make_item(price=None, price_per_child=None, quantity=1):
    return {"price": price, "price_per_child": price_per_child, "quantity": quantity}


class TestResolveItemPrice:
    def test_regular_price(self):
        item = make_item(price=500)
        assert _resolve_item_price(item) == 500

    def test_price_per_child_used_over_price(self):
        item = make_item(price=500, price_per_child=150, quantity=3)
        assert _resolve_item_price(item) == 450  # 150 * 3

    def test_price_per_child_quantity_1(self):
        item = make_item(price_per_child=200, quantity=1)
        assert _resolve_item_price(item) == 200

    def test_no_price_returns_none(self):
        item = make_item()
        assert _resolve_item_price(item) is None


@pytest.mark.asyncio
async def test_get_entry_tariff_weekday():
    """get_entry_tariff returns float for weekday."""
    from app.database.queries.settings import get_entry_tariff

    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value={"value": "300"})

    # 2026-03-30 is Monday (weekday)
    result = await get_entry_tariff(pool, "2026-03-30")
    assert result == 300.0
    pool.fetchrow.assert_awaited_once()
    assert "tariff_weekday" in pool.fetchrow.call_args[0][1]


@pytest.mark.asyncio
async def test_get_entry_tariff_weekend():
    """get_entry_tariff returns weekend tariff for Saturday."""
    from app.database.queries.settings import get_entry_tariff

    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value={"value": "450"})

    # 2026-04-04 is Saturday
    result = await get_entry_tariff(pool, "2026-04-04")
    assert result == 450.0
    assert "tariff_weekend" in pool.fetchrow.call_args[0][1]


@pytest.mark.asyncio
async def test_get_entry_tariff_invalid_value():
    """get_entry_tariff returns 0.0 for invalid setting value."""
    from app.database.queries.settings import get_entry_tariff

    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value={"value": "not_a_number"})

    result = await get_entry_tariff(pool, "2026-03-30")
    assert result == 0.0
