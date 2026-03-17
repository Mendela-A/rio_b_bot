ALTER TABLE ai_usage_log
    ADD COLUMN cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN cache_read_tokens  INTEGER NOT NULL DEFAULT 0;
