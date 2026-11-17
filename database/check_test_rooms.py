import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DB = BASE_DIR / "database" / "hotel_test.db"

connection = sqlite3.connect(TEST_DB)
connection.row_factory = sqlite3.Row

rooms = connection.execute("""
    SELECT
        r.room_number,
        r.housekeeping_status,
        r.maintenance_status
    FROM rooms r
    JOIN room_categories rc
        ON r.category_id = rc.category_id
    WHERE rc.category_name = 'Standard Room'
      AND r.is_active = 1
    ORDER BY r.room_number
""").fetchall()

print("Standard Rooms in Test Database:")
for room in rooms:
    print(
        f"Room {room['room_number']} | "
        f"Housekeeping: {room['housekeeping_status']} | "
        f"Maintenance: {room['maintenance_status']}"
    )

connection.close()