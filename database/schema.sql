
-- ----------------------------------------
-- 1. Users Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS users (

    user_id INTEGER PRIMARY KEY AUTOINCREMENT,

    full_name TEXT NOT NULL,

    email TEXT NOT NULL UNIQUE,

    password_hash TEXT NOT NULL,

    role TEXT NOT NULL
        CHECK (role IN ('Administrator', 'Receptionist', 'Housekeeping Staff')),

    created_at TEXT DEFAULT CURRENT_TIMESTAMP

);

-- ----------------------------------------
-- 2. Guests Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS guests (

    guest_id INTEGER PRIMARY KEY AUTOINCREMENT,

    full_name TEXT NOT NULL,

    email TEXT UNIQUE,

    phone TEXT NOT NULL,

    password_hash TEXT,

    address TEXT,

    id_type TEXT,

    id_number TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP

);

-- ----------------------------------------
-- 3. Room Categories Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS room_categories (

    category_id INTEGER PRIMARY KEY AUTOINCREMENT,

    category_name TEXT NOT NULL UNIQUE,

    description TEXT,

    base_price REAL NOT NULL CHECK (base_price >= 0),

    minimum_guests INTEGER NOT NULL DEFAULT 1,

    maximum_guests INTEGER NOT NULL,

    CHECK (minimum_guests <= maximum_guests)

);

-- ----------------------------------------
-- 4. Rooms Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS rooms (

    room_id INTEGER PRIMARY KEY AUTOINCREMENT,

    room_number TEXT NOT NULL UNIQUE,

    category_id INTEGER NOT NULL,

    floor_number INTEGER,

    housekeeping_status TEXT NOT NULL DEFAULT 'Dirty/Vacant'
        CHECK (
            housekeeping_status IN (
                'Dirty/Vacant',
                'Cleaning In Progress',
                'Clean/Ready'
            )
        ),

    maintenance_status TEXT NOT NULL DEFAULT 'Operational'
        CHECK (
            maintenance_status IN (
                'Operational',
                'Under Maintenance'
            )
        ),

    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),

    FOREIGN KEY (category_id)
        REFERENCES room_categories(category_id)

);

-- ----------------------------------------
-- 5. Reservations Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS reservations (

    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,

    booking_reference TEXT NOT NULL UNIQUE,

    guest_id INTEGER NOT NULL,

    room_id INTEGER NOT NULL,

    checkin_date TEXT NOT NULL,

    checkout_date TEXT NOT NULL,

    number_of_guests INTEGER NOT NULL
        CHECK (number_of_guests > 0),

    booking_status TEXT NOT NULL DEFAULT 'Confirmed'
        CHECK (
            booking_status IN (
                'Confirmed',
                'Cancelled',
                'Checked-in',
                'Checked-out'
            )
        ),

    total_amount REAL NOT NULL DEFAULT 0
        CHECK (total_amount >= 0),

    payment_status TEXT NOT NULL DEFAULT 'Pending'
    CHECK (
        payment_status IN (
            'Pending',
            'Successful',
            'Failed',
            'Refunded',
            'Partially Refunded',
            'No Refund'
        )
    ),

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    CHECK (checkout_date > checkin_date),

    FOREIGN KEY (guest_id)
        REFERENCES guests(guest_id),

    FOREIGN KEY (room_id)
        REFERENCES rooms(room_id)

);

-- ----------------------------------------
-- 6. Reservation Occupants Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS reservation_occupants (

    occupant_id INTEGER PRIMARY KEY AUTOINCREMENT,

    reservation_id INTEGER NOT NULL,

    occupant_name TEXT NOT NULL,

    age INTEGER,

    FOREIGN KEY (reservation_id)
        REFERENCES reservations(reservation_id)
        ON DELETE CASCADE

);

-- ----------------------------------------
-- 7. Seasons Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS seasons (

    season_id INTEGER PRIMARY KEY AUTOINCREMENT,

    season_name TEXT NOT NULL UNIQUE,

    start_month INTEGER NOT NULL
        CHECK (start_month BETWEEN 1 AND 12),

    end_month INTEGER NOT NULL
        CHECK (end_month BETWEEN 1 AND 12),

    price_multiplier REAL NOT NULL
        CHECK (price_multiplier > 0),

    description TEXT

);

-- ----------------------------------------
-- 8. Reservation Nightly Rates Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS reservation_nightly_rates (

    rate_id INTEGER PRIMARY KEY AUTOINCREMENT,

    reservation_id INTEGER NOT NULL,

    stay_date TEXT NOT NULL,

    base_price REAL NOT NULL
        CHECK (base_price >= 0),

    season_multiplier REAL NOT NULL
        CHECK (season_multiplier > 0),

    nightly_price REAL NOT NULL
        CHECK (nightly_price >= 0),

    FOREIGN KEY (reservation_id)
        REFERENCES reservations(reservation_id)
        ON DELETE CASCADE,

    UNIQUE (reservation_id, stay_date)

);

-- ----------------------------------------
-- 9. Housekeeping Assignments Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS housekeeping_assignments (

    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,

    room_id INTEGER NOT NULL,

    assigned_to INTEGER NOT NULL,

    assigned_date TEXT DEFAULT CURRENT_TIMESTAMP,

    started_at TEXT,

    completed_at TEXT,

    cleaning_status TEXT NOT NULL DEFAULT 'Assigned'
        CHECK (
            cleaning_status IN (
                'Assigned',
                'Cleaning In Progress',
                'Completed'
            )
        ),

    remarks TEXT,

    FOREIGN KEY (room_id)
        REFERENCES rooms(room_id),

    FOREIGN KEY (assigned_to)
        REFERENCES users(user_id)

);

-- ----------------------------------------
-- 10. Maintenance Reports Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS maintenance_reports (

    report_id INTEGER PRIMARY KEY AUTOINCREMENT,

    room_id INTEGER NOT NULL,

    reported_by INTEGER NOT NULL,

    issue_description TEXT NOT NULL,

    reported_at TEXT DEFAULT CURRENT_TIMESTAMP,

    resolved_at TEXT,

    maintenance_status TEXT NOT NULL DEFAULT 'Reported'
        CHECK (
            maintenance_status IN (
                'Reported',
                'In Progress',
                'Resolved'
            )
        ),

    remarks TEXT,

    FOREIGN KEY (room_id)
        REFERENCES rooms(room_id),

    FOREIGN KEY (reported_by)
        REFERENCES users(user_id)

);

-- ----------------------------------------
-- 11. Booking Documents Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS booking_documents (

    document_id INTEGER PRIMARY KEY AUTOINCREMENT,

    reservation_id INTEGER NOT NULL,

    document_name TEXT NOT NULL,

    file_path TEXT NOT NULL,

    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reservation_id)
        REFERENCES reservations(reservation_id)
        ON DELETE CASCADE

);

-- ----------------------------------------
-- Payments Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS payments (

    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,

    reservation_id INTEGER NOT NULL,

    payment_reference TEXT NOT NULL UNIQUE,

    payment_method TEXT NOT NULL DEFAULT 'UPI'
        CHECK (
            payment_method IN (
                'UPI',
                'Debit Card',
                'Credit Card',
                'Net Banking'
            )
        ),

    payment_amount REAL NOT NULL
        CHECK (payment_amount >= 0),

    payment_status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (
            payment_status IN (
                'Pending',
                'Successful',
                'Failed',
                'Refunded',
                'Partially Refunded',
                 'No Refund'
            )
        ),

    transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reservation_id)
        REFERENCES reservations(reservation_id)

);

-- ----------------------------------------
-- Payment Attempts Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS payment_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,

    pending_booking_id INTEGER NOT NULL,

    payment_reference TEXT NOT NULL UNIQUE,

    payment_method TEXT NOT NULL DEFAULT 'UPI'
        CHECK (
            payment_method IN (
                'UPI',
                'Debit Card',
                'Credit Card',
                'Net Banking'
            )
        ),

    payment_amount REAL NOT NULL
        CHECK (payment_amount >= 0),

    payment_status TEXT NOT NULL
        CHECK (payment_status IN ('Successful', 'Failed')),

    transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pending_booking_id)
        REFERENCES pending_bookings(pending_booking_id)
);

-- ----------------------------------------
-- Room Holds Table
-- ----------------------------------------
CREATE TABLE IF NOT EXISTS room_holds (
    hold_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    guest_id INTEGER NOT NULL,
    checkin_date TEXT NOT NULL,
    checkout_date TEXT NOT NULL,
    hold_expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id),

    CHECK (checkout_date > checkin_date)
);

-- ----------------------------------------
-- Pending Bookings Table
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS pending_bookings (
    pending_booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_reference TEXT NOT NULL UNIQUE,
    guest_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    checkin_date TEXT NOT NULL,
    checkout_date TEXT NOT NULL,
    number_of_guests INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    booking_data TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'Expired', 'Failed', 'Completed')),

    FOREIGN KEY (guest_id) REFERENCES guests(guest_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),

    CHECK (checkout_date > checkin_date)
);

-- ----------------------------------------
-- Stores cancellation and refund details for reservations
-- ----------------------------------------

CREATE TABLE IF NOT EXISTS refunds (

    refund_id INTEGER PRIMARY KEY AUTOINCREMENT,

    payment_id INTEGER NOT NULL,

    reservation_id INTEGER NOT NULL,

    cancellation_time TEXT NOT NULL,

    refund_percentage REAL NOT NULL
        CHECK (refund_percentage IN (0, 50, 100)),

    refund_amount REAL NOT NULL
        CHECK (refund_amount >= 0),

    refund_status TEXT NOT NULL
        CHECK (refund_status IN ('Processed', 'Not Eligible')),

    FOREIGN KEY (payment_id)
        REFERENCES payments(payment_id),

    FOREIGN KEY (reservation_id)
        REFERENCES reservations(reservation_id),

    UNIQUE (reservation_id)

);