PROJECT_START.md
RIO Telegram Bot – MVP Architecture
🎯 Мета

Створити Telegram-бота для дитячого розважального центру «РІО» з можливістю:

показувати головне меню

динамічно підвантажувати послуги з PostgreSQL

мати правильну архітектуру для майбутнього розширення (cart, booking, Telegram-сповіщення)

🏗 Технологічний стек

Python 3.12

aiogram 3.x

PostgreSQL 16

asyncpg

Docker + Docker Compose

pgAdmin 4

python-dotenv

📦 Структура проекту
rio-bot/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database/
│   │   ├── connection.py
│   │   └── queries.py
│   ├── handlers/
│   │   ├── start.py
│   │   └── services.py
│   └── keyboards/
│       ├── main_menu.py
│       └── services_keyboard.py
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── init.sql
🐳 Docker Compose
version: '3.9'

services:
  postgres:
    image: postgres:16
    container_name: rio_postgres
    environment:
      POSTGRES_DB: rio
      POSTGRES_USER: rio_user
      POSTGRES_PASSWORD: rio_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  pgadmin:
    image: dpage/pgadmin4
    container_name: rio_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@rio.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

  bot:
    build: .
    container_name: rio_bot
    command: python app/main.py
    env_file:
      - .env
    depends_on:
      - postgres

volumes:
  postgres_data:
🐍 Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app/main.py"]
📦 requirements.txt
aiogram==3.*
asyncpg
python-dotenv
🗄 База даних – init.sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    category_id INT REFERENCES categories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_services_category ON services(category_id);
CREATE INDEX idx_services_active ON services(is_active);
🔐 .env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

DB_HOST=postgres
DB_PORT=5432
DB_NAME=rio
DB_USER=rio_user
DB_PASSWORD=rio_pass
🤖 Логіка бота (MVP)
/start

Повідомлення:

Вітаємо у дитячому розважальному центрі «РІО» 💛
Раді бачити вас! Оберіть, будь ласка, що вас цікавить:

Inline кнопки:

1️⃣ Додаткові послуги
2️⃣ Аніматор на виїзд
3️⃣ Інформація про заклад
4️⃣ Програми та аніматори

🔘 Поведінка кнопок
Додаткові послуги
SELECT id, name, price
FROM services
JOIN categories ON services.category_id = categories.id
WHERE categories.type = 'venue'
AND services.is_active = true;
Аніматор на виїзд
WHERE categories.type = 'offsite'
Програми та аніматори
WHERE categories.type = 'program'
🧠 Вимоги до реалізації

Повністю async

Використовувати asyncpg connection pool

Розділення логіки:

handlers

keyboards

database

Динамічна генерація InlineKeyboard

Поки що без корзини

Без складної FSM на цьому етапі

⚙ Робочий процес

docker compose up -d

Відкрити pgAdmin: http://localhost:5050

Додати сервер:

Host: postgres

User: rio_user

Password: rio_pass

Виконати init.sql

Додати категорії:

venue
offsite
program
info

Додати послуги вручну через pgAdmin

Запустити бота

🔮 Архітектурна готовність до масштабування

Ця структура дозволяє без рефакторингу додати:

carts

id

user_id

status

created_at

cart_items

cart_id

service_id

quantity

bookings

customer_name

phone

booking_date

start_time

total_price

status

booking_items

booking_id

service_id

quantity

price_snapshot

📲 Майбутній функціонал

Після підтвердження замовлення:

створення booking

надсилання повідомлення адміністраторам через Telegram Bot API

контроль зайнятості часу

перевірка доступності

✅ Очікуваний результат MVP

Бот запускається в Docker

Показує меню

Підтягує послуги з PostgreSQL

Готовий до впровадження корзини та бронюванняdir
