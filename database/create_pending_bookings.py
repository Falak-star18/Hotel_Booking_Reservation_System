from database.db import get_db_connection

connection = get_db_connection()

try:
    connection.execute("""
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

            FOREIGN KEY (guest_id) REFERENCES guests(guest_id),
            FOREIGN KEY (room_id) REFERENCES rooms(room_id),

            CHECK (checkout_date > checkin_date)
        )
    """)

    connection.commit()
    print("Pending bookings table created successfully!")

except Exception as error:
    connection.rollback()
    print("Error:", error)

finally:
    connection.close()