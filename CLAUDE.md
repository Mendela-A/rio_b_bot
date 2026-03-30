# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run tests
python -m pytest tests/ -v

# Run single test file
python -m pytest tests/test_booking_text.py -v

# Run bot (polling)
python -m app.main

# Apply migration manually
psql $DATABASE_URL -f migrations/XXX_name.sql
```

## Architecture

**Stack:** Python, aiogram 3.26, asyncpg, PostgreSQL, aiohttp (webhook mode)

**Entry point:** `app/main.py` — creates `Bot`, `Dispatcher`, registers routers, starts polling or webhook (port 8081).

**Config:** `app/config.py` — loads from `.env`. Key vars: `BOT_TOKEN`, `DB_*`, `ADMIN_CHAT_ID`, `WEBHOOK_URL`.

### Handlers (`app/handlers/`)
| File | Responsibility |
|------|----------------|
| `booking.py` | Main booking FSM, cart confirm, my-bookings, change requests, admin callbacks (`adm:*`) |
| `cart.py` | Service selection, cart add/remove, quantity for price_per_child |
| `admin.py` | Admin stats, booking lists, `/test_notify` command; `is_admin()` checks group membership |
| `services.py` | Service catalogue browse |
| `_utils.py` | Pure helpers: `services_lines()`, `confirmation_text()`, `cart_text()`, `fmt_date()` |
| `ai_chat.py` | Anthropic AI assistant |

### Database queries (`app/database/queries/`)
| File | Key functions |
|------|---------------|
| `bookings.py` | `create_booking`, `create_booking_items`, `get_user_bookings`, `get_booking_items`, `apply_change_request`, `create_change_request/items` |
| `cart.py` | `cart_get`, `cart_add`, `cart_clear` |
| `settings.py` | `get_entry_tariff(pool, date)` → float (tariff_weekday / tariff_weekend) |
| `services.py` | `get_service_by_id`, category/service listing |

### Key data flow: booking confirmation (`booking.py: booking_confirm`)
1. `create_booking()` → booking_id
2. `entry_rate = await get_entry_tariff()` (default 0 if error)
3. Insert entry fee row into `booking_items` (service_id=NULL, label "Вхід (будні/вихідні)")
4. `create_booking_items()` — snapshots cart into booking_items
5. `asyncio.create_task(_notify_admin(...))` — fires notification asynchronously
6. `edit_text` shows success to user

### Pricing rules
- Services have `price` (fixed) and `price_per_child` (per child, takes priority)
- `_resolve_item_price(item)` → `ppc * qty` or `price`
- Entry fee: stored in settings as `tariff_weekday` / `tariff_weekend`, multiplied by `children_count`
- Display logic: `services_lines()` in `_utils.py`

### Admin notifications
- All go to `ADMIN_CHAT_ID` (group chat)
- `_notify_admin()` — new booking with confirm/reject buttons (`adm:ok/no:{id}`)
- `_notify_admin_change_request()` — change request with approve/reject buttons (`adm:chg_ok/no:{id}`)
- Errors logged with `exc_info=True`; `/test_notify` command to diagnose connectivity

### Change request flow
`ChangeStates`: `waiting_date` → `waiting_children` → `confirming`
- Existing booking items loaded into cart (excluding entry fee, which has `service_id=NULL`)
- `create_change_request` + `create_change_items` → admin notified
- On approval: `apply_change_request()` replaces booking_items atomically

### FSM states
- `BookingStates` — full booking flow (name → phone → children → adults → birthday → date → confirm)
- `ChangeStates` — booking modification
- `BookingStates.quick_*` — quick booking from service card

### Tests (`tests/`)
Pure unit tests, no DB or aiogram mocks needed. Each test file mirrors a logical domain:
- `test_booking_text.py` / `test_booking_scenarios.py` — `confirmation_text`, `services_lines`
- `test_admin_notify.py` / `test_change_notify.py` — notification text building
- `test_my_bookings.py` — `_my_bookings_text` display
- `test_entry_rate_guard.py` — regression for entry_rate NameError fix
- `test_pricing.py`, `test_price_per_child.py`, `test_service_label.py` — price calculation
- `test_cart_text.py`, `test_utils.py` — utility functions
