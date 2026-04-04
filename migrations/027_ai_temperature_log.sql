ALTER TABLE ai_usage_log ADD COLUMN temperature REAL;

INSERT INTO schema_migrations (version) VALUES (27);
