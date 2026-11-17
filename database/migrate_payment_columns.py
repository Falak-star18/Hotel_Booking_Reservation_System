from database.db import get_db_connection


connection = get_db_connection()

try:
    # Check which columns already exist
    columns = [
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(reservations)"
        ).fetchall()
    ]

    # Add payment_status if it does not exist
    if "payment_status" not in columns:
        connection.execute(
            """
            ALTER TABLE reservations
            ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'Pending'
            CHECK (
                payment_status IN (
                    'Pending',
                    'Successful',
                    'Failed',
                    'Refunded',
                    'Partially Refunded'
                )
            )
            """
        )
        print("payment_status column added.")

    # Add cancelled_at if it does not exist
    if "cancelled_at" not in columns:
        connection.execute(
            """
            ALTER TABLE reservations
            ADD COLUMN cancelled_at TEXT
            """
        )
        print("cancelled_at column added.")

    connection.commit()
    print("Database migration completed successfully.")

except Exception as error:
    connection.rollback()
    print("Migration failed:", error)

finally:
    connection.close()