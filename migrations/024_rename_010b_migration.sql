-- Remove stale tracking entry for the old migration name (010b_ was already applied)
DELETE FROM schema_migrations WHERE version = '010_services_fk_set_null';
