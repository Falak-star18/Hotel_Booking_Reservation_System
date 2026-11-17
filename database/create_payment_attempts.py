from database.db import get_db_connection


def create_payment_attempts_table():
    connection = get_db_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS payment_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pending_booking_id INTEGER NOT NULL,
                payment_reference TEXT NOT NULL UNIQUE,
                payment_method TEXT NOT NULL,
                payment_amount REAL NOT NULL,
                payment_status TEXT NOT NULL
                    CHECK (payment_status IN ('Successful', 'Failed')),
                attempt_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pending_booking_id)
                    REFERENCES pending_bookings(pending_booking_id)
                    ON DELETE CASCADE
            )
        """)

        connection.commit()
        print("Payment attempts table created successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    create_payment_attempts_table()