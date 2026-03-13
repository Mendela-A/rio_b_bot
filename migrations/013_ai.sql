-- 1. База знань Q&A
CREATE TABLE ai_qa_pairs (
    id         SERIAL PRIMARY KEY,
    question   TEXT        NOT NULL,
    answer     TEXT        NOT NULL,
    is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
    sort_order INTEGER     NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ai_qa_pairs_active_sort ON ai_qa_pairs (is_active, sort_order, id);

-- 2. Історія діалогів (зберігається між сесіями/рестартами)
CREATE TABLE ai_chat_history (
    id          SERIAL PRIMARY KEY,
    telegram_id BIGINT      NOT NULL,
    role        TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ai_chat_history_user ON ai_chat_history (telegram_id, created_at);

-- 3. Лог використання токенів
CREATE TABLE ai_usage_log (
    id            SERIAL PRIMARY KEY,
    telegram_id   BIGINT  NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ai_usage_log_date ON ai_usage_log (created_at);

-- 4. Налаштування AI (через існуючу таблицю settings)
INSERT INTO settings (key, value) VALUES
    ('ai_enabled',             'true'),
    ('ai_company_description', 'Дитячий розважальний заклад «РІО» у Чернівцях. Телефон для зв''язку: (ваш телефон).'),
    ('ai_welcome_message',     'Привіт! 👋 Напишіть своє запитання — я відповім на основі інформації про наш заклад.'),
    ('ai_max_tokens',          '1024'),
    ('ai_history_limit',       '20')
ON CONFLICT (key) DO NOTHING;

-- 5. Кнопка в меню
INSERT INTO bot_texts (key, hint, default_value) VALUES
    ('menu.btn_ai_chat', 'Кнопка AI Асистент у головному меню', '🤖 Асистент')
ON CONFLICT (key) DO NOTHING;

INSERT INTO schema_migrations (version) VALUES (13);
