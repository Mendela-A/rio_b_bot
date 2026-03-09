CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Mark all already-applied migrations as done
INSERT INTO schema_migrations (version) VALUES
    ('003_bot_texts_registry'),
    ('004_services_photo_url_sort_order'),
    ('005_booking_change_requests'),
    ('006_users_broadcast'),
    ('007_admin_superadmin'),
    ('008_categories_sort_order'),
    ('009_indexes')
ON CONFLICT (version) DO NOTHING;
