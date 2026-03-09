CREATE TABLE users (
    telegram_id  BIGINT PRIMARY KEY,
    first_name   TEXT,
    username     TEXT,
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE broadcasts (
    id           SERIAL PRIMARY KEY,
    text         TEXT NOT NULL,
    photo_url    TEXT,
    status       TEXT DEFAULT 'pending',
    sent_count   INT  DEFAULT 0,
    failed_count INT  DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    finished_at  TIMESTAMPTZ
);
