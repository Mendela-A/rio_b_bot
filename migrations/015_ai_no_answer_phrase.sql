INSERT INTO settings (key, value) VALUES
    ('ai_no_answer_phrase', 'немає цієї інформації')
ON CONFLICT (key) DO NOTHING;

INSERT INTO schema_migrations (version) VALUES (15);
