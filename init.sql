CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    category_id INT REFERENCES categories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    price NUMERIC(10,2),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INT DEFAULT 0,
    parent_id INT REFERENCES services(id) ON DELETE CASCADE
);

CREATE TABLE info_pages (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    sort_order INT DEFAULT 0
);

CREATE INDEX idx_services_category ON services(category_id);
CREATE INDEX idx_services_active ON services(is_active);

-- Cart (temporary, before booking confirmation)
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    service_id INT REFERENCES services(id) ON DELETE CASCADE,
    quantity INT DEFAULT 1,
    UNIQUE(telegram_id, service_id)
);

-- Bookings
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    children_count INT NOT NULL,
    booking_date DATE NOT NULL,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Services snapshot in booking
CREATE TABLE booking_items (
    id SERIAL PRIMARY KEY,
    booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,
    service_id INT REFERENCES services(id),
    service_name TEXT NOT NULL,
    price NUMERIC(10,2),
    quantity INT DEFAULT 1
);

-- Seed: categories
INSERT INTO categories (name, type) VALUES
    ('Додаткові послуги', 'venue'),
    ('Аніматор на виїзд', 'offsite'),
    ('Програми та аніматори', 'program');

-- Seed: services
INSERT INTO services (category_id, name, price, description, is_active, sort_order) VALUES
    (1, 'Оренда залу (2 год)', 500.00, 'Повна оренда святкового залу на 2 години', true, 1),
    (1, 'Фотозона', 300.00, 'Декорована фотозона з реквізитом', true, 2),
    (1, 'Торт на замовлення', 450.00, 'Святковий торт від наших кондитерів', true, 3),
    (2, 'Аніматор (1 год)', 800.00, 'Виїзд аніматора на 1 годину', true, 1),
    (2, 'Аніматор (2 год)', 1400.00, 'Виїзд аніматора на 2 години', true, 2),
    (2, 'Аніматор + реквізит', 1800.00, 'Виїзд аніматора з повним набором реквізиту', true, 3),
    (3, 'Програма "Супергерої"', 1200.00, 'Розважальна програма з костюмами супергероїв', true, 1),
    (3, 'Програма "Принцеси"', 1200.00, 'Казкова програма з принцесами', true, 2),
    (3, 'Програма "Пірати"', 1100.00, 'Пригодницька програма для юних піратів', true, 3);

-- Bot editable texts
CREATE TABLE bot_texts (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Seed: info_pages
INSERT INTO info_pages (title, content, sort_order) VALUES
    ('📍 Адреса', 'м. Київ, вул. Прикладна, 1', 1),
    ('🕐 Графік роботи', 'Понеділок – П''ятниця: 10:00 – 20:00
Субота – Неділя: 09:00 – 21:00', 2),
    ('📞 Контакти', 'Телефон: +380 XX XXX XX XX
Email: info@rio-kids.ua', 3),
    ('ℹ️ Про заклад', 'РІО — сучасний дитячий розважальний центр.
Ми створюємо незабутні свята для ваших дітей!', 4);
