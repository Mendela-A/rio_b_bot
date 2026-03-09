ALTER TABLE categories ADD COLUMN IF NOT EXISTS sort_order INTEGER;
UPDATE categories SET sort_order = id WHERE sort_order IS NULL;
