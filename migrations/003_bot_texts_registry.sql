-- Migration 003: store bot text registry in DB (hints + defaults)
-- bot_texts.value becomes nullable: NULL = not overridden (use default_value)

ALTER TABLE bot_texts ALTER COLUMN value DROP NOT NULL;
ALTER TABLE bot_texts ADD COLUMN IF NOT EXISTS hint TEXT NOT NULL DEFAULT '';
ALTER TABLE bot_texts ADD COLUMN IF NOT EXISTS default_value TEXT NOT NULL DEFAULT '';

INSERT INTO bot_texts (key, hint, default_value) VALUES
  ('menu.greeting',       'Привітання при /start',                              E'Вітаємо у дитячому розважальному центрі \u00abРІО\u00bb \U0001f49b\nРаді бачити вас! Оберіть, будь ласка, що вас цікавить:'),
  ('booking.ask_name',    'Запит імені (крок 1)',                               E'\U0001f4dd Введіть прізвище та ім''я:'),
  ('booking.ask_phone',   'Запит телефону (крок 2)',                            E'\U0001f4f1 Введіть номер телефону або натисніть кнопку нижче:'),
  ('booking.ask_children','Запит кількості дітей (крок 3)',                     E'\U0001f476 Скільки дітей буде на святі?'),
  ('booking.ask_date',    'Запит дати (крок 4)',                                E'\U0001f4c5 Оберіть дату:'),
  ('booking.success',     'Підтвердження бронювання — {id} = номер бронювання', E'\u2705 Бронювання #{id} прийнято!\n\nМи зв''яжемося з вами для підтвердження.'),
  ('booking.cancelled',   'Повідомлення про скасування',                        'Бронювання скасовано.'),
  ('cart.added',          'Спливаюче при додаванні послуги',                    E'\u2705 Додано до кошика!'),
  ('cart.empty',          'Порожній кошик',                                     E'\U0001f6d2 Кошик порожній.')
ON CONFLICT (key) DO UPDATE SET
  hint          = EXCLUDED.hint,
  default_value = EXCLUDED.default_value;
