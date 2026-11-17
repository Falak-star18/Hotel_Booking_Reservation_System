from database.db import get_db_connection

connection = get_db_connection()

try:
    connection.execute("""
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
                        'Partially Refunded'
                    )
                ),

            transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (reservation_id)
                REFERENCES reservations(reservation_id)
        )
    """)

    connection.commit()
    print("Payments table created successfully.")

except Exception as error:
    connection.rollback()
    print("Migration failed:", error)

finally:
    connection.close()