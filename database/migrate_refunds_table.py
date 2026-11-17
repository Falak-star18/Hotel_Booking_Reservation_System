from database.db import get_db_connection

connection = get_db_connection()

try:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS refunds (

            refund_id INTEGER PRIMARY KEY AUTOINCREMENT,

            payment_id INTEGER NOT NULL,

            reservation_id INTEGER NOT NULL,

            cancellation_time TEXT NOT NULL,

            refund_percentage REAL NOT NULL
                CHECK (refund_percentage IN (0, 50, 100)),

            refund_amount REAL NOT NULL
                CHECK (refund_amount >= 0),

            refund_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK (
                    refund_status IN (
                        'Pending',
                        'Processed',
                        'Not Eligible'
                    )
                ),

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (payment_id)
                REFERENCES payments(payment_id),

            FOREIGN KEY (reservation_id)
                REFERENCES reservations(reservation_id)
        )
    """)

    connection.commit()
    print("Refunds table created successfully.")

except Exception as error:
    connection.rollback()
    print("Migration failed:", error)

finally:
    connection.close()