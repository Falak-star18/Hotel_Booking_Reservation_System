import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "hotel.db"

connection = sqlite3.connect(DATABASE_PATH)

try:
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("BEGIN IMMEDIATE")

    # Update payments table constraint
    connection.execute("""
        CREATE TABLE payments_new (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            payment_reference TEXT NOT NULL UNIQUE,
            payment_method TEXT NOT NULL DEFAULT 'UPI'
                CHECK (payment_method IN (
                    'UPI', 'Debit Card', 'Credit Card', 'Net Banking'
                )),
            payment_amount REAL NOT NULL CHECK (payment_amount >= 0),
            payment_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK (payment_status IN (
                    'Pending', 'Successful', 'Failed',
                    'Refunded', 'Partially Refunded', 'No Refund'
                )),
            transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reservation_id)
                REFERENCES reservations(reservation_id)
        )
    """)

    connection.execute("""
        INSERT INTO payments_new
        SELECT * FROM payments
    """)

    connection.execute("DROP TABLE payments")
    connection.execute("ALTER TABLE payments_new RENAME TO payments")

    # Update reservations table constraint
    connection.execute("""
        CREATE TABLE reservations_new (
            reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_reference TEXT NOT NULL UNIQUE,
            guest_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,
            checkout_date TEXT NOT NULL,
            number_of_guests INTEGER NOT NULL
                CHECK (number_of_guests > 0),
            booking_status TEXT NOT NULL DEFAULT 'Confirmed'
                CHECK (booking_status IN (
                    'Confirmed', 'Cancelled', 'Checked-in', 'Checked-out'
                )),
            total_amount REAL NOT NULL DEFAULT 0
                CHECK (total_amount >= 0),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            payment_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK (payment_status IN (
                    'Pending', 'Successful', 'Failed',
                    'Refunded', 'Partially Refunded', 'No Refund'
                )),
            cancelled_at TEXT,
            CHECK (checkout_date > checkin_date),
            FOREIGN KEY (guest_id) REFERENCES guests(guest_id),
            FOREIGN KEY (room_id) REFERENCES rooms(room_id)
        )
    """)

    connection.execute("""
        INSERT INTO reservations_new
        SELECT * FROM reservations
    """)

    connection.execute("DROP TABLE reservations")
    connection.execute(
        "ALTER TABLE reservations_new RENAME TO reservations"
    )

    connection.commit()
    print("Test database migration completed successfully.")

except Exception:
    connection.rollback()
    raise

finally:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.close()