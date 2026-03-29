INSERT INTO settings (key, value) VALUES
  ('tariff_weekday', '0'),
  ('tariff_weekend', '0')
ON CONFLICT (key) DO NOTHING;
