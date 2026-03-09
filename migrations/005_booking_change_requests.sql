CREATE TABLE booking_change_requests (
    id SERIAL PRIMARY KEY,
    booking_id INT REFERENCES bookings(id) ON DELETE CASCADE,
    proposed_date DATE NOT NULL,
    proposed_children_count INT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE booking_change_items (
    id SERIAL PRIMARY KEY,
    change_request_id INT REFERENCES booking_change_requests(id) ON DELETE CASCADE,
    service_id INT REFERENCES services(id),
    service_name TEXT NOT NULL,
    price NUMERIC(10,2),
    quantity INT DEFAULT 1
);
