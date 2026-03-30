-- Add CHECK constraints on status columns to prevent invalid values

ALTER TABLE bookings
    ADD CONSTRAINT bookings_status_check
    CHECK (status IN ('new', 'confirmed', 'cancelled'));

ALTER TABLE booking_change_requests
    ADD CONSTRAINT booking_change_requests_status_check
    CHECK (status IN ('pending', 'approved', 'rejected'));
