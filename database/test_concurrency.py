import sqlite3
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import uuid

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DB = BASE_DIR / "database" / "hotel_test.db"

CHECKIN = "2026-11-15"
CHECKOUT = "2026-11-17"
CATEGORY_ID = 1  # Standard Room
GUEST_COUNT = 2

# Make both requests start together
start_barrier = threading.Barrier(2)


def book_room(guest_name):
    connection = sqlite3.connect(TEST_DB, timeout=30)
    connection.row_factory = sqlite3.Row

    try:
        # Both requests begin at approximately the same time
        start_barrier.wait()

        # Lock the database before checking room availability
        connection.execute("BEGIN IMMEDIATE")

        # Find the first eligible Standard Room
        room = connection.execute(
            """
            SELECT r.room_id, r.room_number
            FROM rooms r
            WHERE r.category_id = ?
              AND r.is_active = 1
              AND r.maintenance_status = 'Operational'
              AND r.housekeeping_status = 'Clean/Ready'
              AND NOT EXISTS (
                  SELECT 1
                  FROM reservations res
                  WHERE res.room_id = r.room_id
                    AND res.booking_status IN ('Confirmed', 'Checked-in')
                    AND res.checkin_date < ?
                    AND res.checkout_date > ?
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM maintenance_reports mr
                  WHERE mr.room_id = r.room_id
                    AND mr.maintenance_status IN ('Reported', 'In Progress')
              )
            ORDER BY r.room_number
            LIMIT 1
            """,
            (CATEGORY_ID, CHECKOUT, CHECKIN)
        ).fetchone()

        if room is None:
            connection.rollback()
            return f"{guest_name}: No room available."

        # Create a test guest
        cursor = connection.execute(
            """
            INSERT INTO guests (full_name, email, phone)
            VALUES (?, ?, ?)
            """,
            (
                guest_name,
                f"{uuid.uuid4().hex}@example.com",
                "9999999999"
            )
        )
        guest_id = cursor.lastrowid

        # Create the reservation
        booking_reference = "TEST-" + uuid.uuid4().hex[:10].upper()

        connection.execute(
            """
            INSERT INTO reservations (
                booking_reference,
                guest_id,
                room_id,
                checkin_date,
                checkout_date,
                number_of_guests,
                booking_status,
                total_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Confirmed', ?)
            """,
            (
                booking_reference,
                guest_id,
                room["room_id"],
                CHECKIN,
                CHECKOUT,
                GUEST_COUNT,
                12000
            )
        )

        connection.commit()

        return (
            f"{guest_name}: Assigned Room {room['room_number']} "
            f"({booking_reference})"
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            book_room,
            ["Guest A", "Guest B"]
        ))

    print("\nConcurrency Test Results:")
    for result in results:
        print(result)