# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram-бот для дитячого розважального центру «РІО». Повністю async, aiogram 3.x, PostgreSQL через asyncpg.

## Commands

```bash
# Запуск (Docker)
docker compose up -d

# Логи бота
docker compose logs -f bot

# Зупинка
docker compose down

# Локальна розробка (без Docker)
source venv/bin/activate
python app/main.py
```

## Architecture

```
app/
├── main.py              # Точка входу: ініціалізація dp, bot, DB pool, запуск polling
├── config.py            # Завантаження .env через python-dotenv
├── database/
│   ├── connection.py    # asyncpg connection pool (створення/закриття)
│   └── queries.py       # Всі SQL-запити (лише SELECT на MVP)
├── handlers/
│   ├── start.py         # /start — головне меню
│   └── services.py      # callback_query handlers для кнопок меню
└── keyboards/
    ├── main_menu.py     # InlineKeyboardMarkup головного меню
    └── services_keyboard.py  # Динамічна генерація клавіатури зі списком послуг
```

## Key conventions

- DB pool створюється при старті і передається через `bot.data` або middleware
- Всі handlers — async, використовують `await`
- Keyboards генеруються динамічно з даних БД (не хардкодяться)
- Категорії послуг: `venue`, `offsite`, `program`, `info`
- `.env` містить `BOT_TOKEN`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

## Database schema

```sql
categories (id, name, type)           -- type: venue | offsite | program | info
services (id, category_id, name, price, description, is_active)
```

## Future tables (not yet implemented)

`carts`, `cart_items`, `bookings`, `booking_items` — структура описана в readme.md
