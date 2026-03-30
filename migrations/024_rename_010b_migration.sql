-- Rename tracking entry for migration that was renamed from 010_ to 010b_
UPDATE schema_migrations
SET version = '010b_services_fk_set_null'
WHERE version = '010_services_fk_set_null';
