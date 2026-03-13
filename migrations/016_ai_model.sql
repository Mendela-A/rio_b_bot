INSERT INTO settings (key, value) VALUES
    ('ai_model', 'claude-3-5-haiku-20241022')
ON CONFLICT (key) DO NOTHING;

INSERT INTO schema_migrations (version) VALUES (16);
