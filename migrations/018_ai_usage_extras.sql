ALTER TABLE ai_usage_log
    ADD COLUMN response_ms INTEGER,
    ADD COLUMN model       TEXT;
