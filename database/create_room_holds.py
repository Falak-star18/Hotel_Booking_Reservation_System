from database.db import get_db_connection

connection = get_db_connection()

try:
    connection.execute("""
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
        )
    """)

    connection.commit()
    print("Room holds table created successfully!")

except Exception as error:
    connection.rollback()
    print("Error:", error)

finally:
    connection.close()