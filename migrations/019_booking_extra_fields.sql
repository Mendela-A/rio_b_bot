ALTER TABLE bookings
  ADD COLUMN IF NOT EXISTS adults_count INTEGER,
  ADD COLUMN IF NOT EXISTS birthday_person_name TEXT,
  ADD COLUMN IF NOT EXISTS birthday_person_date DATE;

INSERT INTO bot_texts (key, hint, value) VALUES
  ('booking.ask_adults',        'Запит кількості дорослих (крок 4)',  '👨 Скільки дорослих буде на святі?'),
  ('booking.ask_birthday_name', 'Запит імені іменинника (крок 5)',    '🎂 Як звати іменинника/іменинницю?'),
  ('booking.ask_birthday_date', 'Запит дати народження (крок 6)',     '📅 Введіть дату народження іменинника (формат: ДД.ММ.РРРР):')
ON CONFLICT (key) DO NOTHING;
