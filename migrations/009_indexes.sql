-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_bookings_status      ON bookings (status);
CREATE INDEX IF NOT EXISTS idx_bookings_created_at  ON bookings (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_booking_items_booking ON booking_items (booking_id);
CREATE INDEX IF NOT EXISTS idx_services_category    ON services (category_id);
CREATE INDEX IF NOT EXISTS idx_services_parent      ON services (parent_id);
CREATE INDEX IF NOT EXISTS idx_inquiries_created_at ON inquiries (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_is_active      ON users (is_active) WHERE is_active = TRUE;
