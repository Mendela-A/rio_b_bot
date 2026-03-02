# RIO Bot — Development Plan

## Технічні рішення (прийнято)
- Python **3.13** (відповідає локальному venv)
- aiogram **3.17.0**
- Логування: `logging` → stdout (INFO рівень, формат: `time | level | message`)
- Пагінація клавіатури: **не в MVP**, залишити як TODO
- Невідомий текст від юзера: **ігнорувати**

---

## Схема БД (фінальна)

```sql
categories     (id, name, type)                          -- type: venue | offsite | program | info
services       (id, category_id, name, price,
                description, is_active, order)
info_pages     (id, title, content, order)               -- Контакти / Адреса / Графік і т.д.
```

## UX Flow

```
/start
└── Головне меню (4 кнопки)
    ├── 1. Бронювання              → "Функція в розробці 🔧"  (заглушка)
    ├── 2. Додаткові послуги       → список послуг (venue)    + [Назад] [Головне меню]
    ├── 3. Аніматор на виїзд      → список послуг (offsite)   + [Назад] [Головне меню]
    ├── 4. Програми та аніматори  → список послуг (program)   + [Назад] [Головне меню]
    └── 5. Інформація про заклад  → список info_pages         + [Назад] [Головне меню]
            └── [сторінка]        → текст контенту            + [Назад] [Головне меню]
```

---

## Блоки розробки

### Block 1 — Scaffold
- [ ] Створити структуру папок `app/`
- [ ] `.gitignore`
- [ ] `requirements.txt`
- [ ] `.env.example`

### Block 2 — Docker
- [ ] `Dockerfile` (python:3.13-slim)
- [ ] `docker-compose.yml` з healthcheck для postgres
- [ ] Монтування `init.sql` → `/docker-entrypoint-initdb.d/`
- [ ] Volume для pgAdmin

### Block 3 — Database
- [ ] `init.sql` з таблицями: categories, services, info_pages + індекси + seed-дані
- [ ] `app/database/connection.py` — asyncpg pool (create/close)
- [ ] `app/database/queries.py` — всі запити:
  - `get_services_by_type(pool, type)`
  - `get_info_pages(pool)`
  - `get_info_page_by_id(pool, id)`

### Block 4 — Config
- [ ] `app/config.py` — dataclass з полів .env (BOT_TOKEN, DB_*, ADMIN_CHAT_ID)
- [ ] Валідація при завантаженні (якщо поле порожнє — exception)

### Block 5 — Keyboards
- [ ] `app/keyboards/main_menu.py` — статична InlineKeyboard (4 кнопки)
- [ ] `app/keyboards/services_kb.py` — динамічна зі списку послуг + [Назад][Головне меню]
- [ ] `app/keyboards/info_kb.py` — динамічна зі списку info_pages + [Назад][Головне меню]
- [ ] `app/keyboards/nav_kb.py` — [Назад][Головне меню] для контент-сторінок

### Block 6 — Handlers
- [ ] `app/handlers/start.py` — `/start`, показ головного меню
- [ ] `app/handlers/services.py` — callback: venue / offsite / program
- [ ] `app/handlers/info.py` — callback: info_list → info_page

### Block 7 — main.py
- [ ] Ініціалізація логера
- [ ] Завантаження config
- [ ] Створення DB pool (startup) / закриття (shutdown)
- [ ] Реєстрація роутерів
- [ ] Запуск polling

### Block 8 — Запуск і перевірка
- [ ] `docker compose up -d`
- [ ] Перевірка `/start`
- [ ] Перевірка всіх 4 кнопок
- [ ] Перевірка навігації Назад / Головне меню

---

## .env.example
```
BOT_TOKEN=
DB_HOST=postgres
DB_PORT=5432
DB_NAME=rio
DB_USER=rio_user
DB_PASSWORD=rio_pass
ADMIN_CHAT_ID=
```

---

## TODO (після MVP)
- Пагінація клавіатури (якщо послуг > 8)
- Кошик (carts, cart_items)
- Бронювання (bookings, booking_items)
- Сповіщення адміну через ADMIN_CHAT_ID
