from database.db import get_db_connection


def migrate_pending_booking_status():
    connection = get_db_connection()

    try:
        columns = connection.execute(
            "PRAGMA table_info(pending_bookings)"
        ).fetchall()

        column_names = [column["name"] for column in columns]

        if "status" not in column_names:
            connection.execute("""
                ALTER TABLE pending_bookings
                ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'
                CHECK (
                    status IN (
                        'Pending',
                        'Completed',
                        'Failed',
                        'Expired'
                    )
                )
            """)

            connection.commit()
            print("Pending booking status column added successfully.")

        else:
            print("Status column already exists.")

    finally:
        connection.close()


if __name__ == "__main__":
    migrate_pending_booking_status()