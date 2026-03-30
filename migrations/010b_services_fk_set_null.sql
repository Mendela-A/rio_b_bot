-- Fix FK constraints on service_id to allow service deletion (SET NULL instead of RESTRICT)
-- service_name TEXT snapshot is preserved; service_id is just a soft link

-- booking_items.service_id
ALTER TABLE booking_items DROP CONSTRAINT IF EXISTS booking_items_service_id_fkey;
ALTER TABLE booking_items ADD CONSTRAINT booking_items_service_id_fkey
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL;

-- booking_change_items.service_id
ALTER TABLE booking_change_items DROP CONSTRAINT IF EXISTS booking_change_items_service_id_fkey;
ALTER TABLE booking_change_items ADD CONSTRAINT booking_change_items_service_id_fkey
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL;

-- inquiries.service_id
ALTER TABLE inquiries DROP CONSTRAINT IF EXISTS inquiries_service_id_fkey;
ALTER TABLE inquiries ADD CONSTRAINT inquiries_service_id_fkey
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL;
