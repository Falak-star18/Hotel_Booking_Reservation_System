
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Display the table constraints in both databases
for db_name in ["hotel.db", "hotel_test.db"]:
    db_path = BASE_DIR / db_name

    print(f"\n{'=' * 50}")
    print(f"DATABASE: {db_name}")
    print("=" * 50)

    connection = sqlite3.connect(db_path)

    for table in ["payments", "reservations"]:
        result = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table,)
        ).fetchone()

        print(f"\n{table.upper()} TABLE:")

        if result:
            print(result[0])
        else:
            print("Table not found.")

    connection.close()


# Test whether No Refund is accepted
connection = sqlite3.connect(BASE_DIR / "hotel_test.db")

try:
    connection.execute("""
        CREATE TEMP TABLE refund_status_test (
            payment_status TEXT CHECK (
                payment_status IN (
                    'Pending',
                    'Successful',
                    'Failed',
                    'Refunded',
                    'Partially Refunded',
                    'No Refund'
                )
            )
        )
    """)

    connection.execute(
        "INSERT INTO refund_status_test VALUES (?)",
        ("No Refund",)
    )

    print("\nSUCCESS: No Refund is accepted by SQLite.")

except sqlite3.IntegrityError as error:
    print("\nFAILED:", error)

finally:
    connection.close()


# Verify records and foreign keys in the test database
connection = sqlite3.connect(BASE_DIR / "hotel_test.db")

print("\nTEST DATABASE VALIDATION")

for table in [
    "reservations",
    "payments",
    "refunds",
    "reservation_occupants",
    "reservation_nightly_rates",
    "booking_documents"
]:
    count = connection.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"{table}: {count} records")

foreign_key_errors = connection.execute(
    "PRAGMA foreign_key_check"
).fetchall()

if foreign_key_errors:
    print("\nForeign-key errors found:")
    print(foreign_key_errors)
else:
    print("\nSUCCESS: No foreign-key errors found.")

# Verify the latest cancelled booking and refund
connection = sqlite3.connect(BASE_DIR / "hotel.db")
connection.row_factory = sqlite3.Row

print("\nLATEST CANCELLED BOOKING:")

booking = connection.execute("""
    SELECT reservation_id, booking_reference,
           booking_status, payment_status, total_amount
    FROM reservations
    WHERE booking_status = 'Cancelled'
    ORDER BY reservation_id DESC
    LIMIT 1
""").fetchone()

print(dict(booking) if booking else "No cancelled booking found.")

print("\nLATEST REFUND:")

refund = connection.execute("""
    SELECT *
    FROM refunds
    ORDER BY refund_id DESC
    LIMIT 1
""").fetchone()

print(dict(refund) if refund else "No refund record found.")

# Verify the latest cancelled booking and its refund
connection = sqlite3.connect(BASE_DIR / "hotel.db")
connection.row_factory = sqlite3.Row

booking = connection.execute("""
    SELECT reservation_id, booking_reference,
           booking_status, payment_status, total_amount
    FROM reservations
    WHERE booking_status = 'Cancelled'
    ORDER BY reservation_id DESC
    LIMIT 1
""").fetchone()

print("\nLATEST CANCELLED BOOKING:")
print(dict(booking) if booking else "No cancelled booking found.")

if booking:
    refund = connection.execute("""
        SELECT refund_percentage, refund_amount, refund_status
        FROM refunds
        WHERE reservation_id = ?
    """, (booking["reservation_id"],)).fetchone()

    print("\nREFUND DETAILS:")
    print(dict(refund) if refund else "No refund record found.")

connection = sqlite3.connect("database/hotel.db")

result = connection.execute("""
    SELECT room_id, room_number
    FROM rooms
    WHERE room_number = '102'
""").fetchone()

print("Room 102 details:", result)

connection = sqlite3.connect("database/hotel.db")

rooms = connection.execute("""
    SELECT room_id, room_number, maintenance_status, housekeeping_status
    FROM rooms
    WHERE is_active = 1
""").fetchall()

for room in rooms:
    print(room)


connection = sqlite3.connect("database/hotel.db")

connection.execute("""
    UPDATE rooms
    SET maintenance_status = 'Under Maintenance'
    WHERE room_id = 3
""")

connection.commit()

print("Room 103 marked as Under Maintenance.")



connection = sqlite3.connect("database/hotel.db")

connection.execute("""
    UPDATE rooms
    SET maintenance_status = 'Operational'
    WHERE room_id = 3
""")

connection.commit()

print("Room 103 maintenance status restored to Operational.")


connection = sqlite3.connect("database/hotel.db")

connection.execute("""
    UPDATE rooms
    SET housekeeping_status = 'Clean/Ready'
    WHERE room_id = 3
""")

connection.commit()

print("Room 103 housekeeping status restored to Clean/Ready.")

import sqlite3

connection = sqlite3.connect("database/hotel.db")
connection.row_factory = sqlite3.Row

reservations = connection.execute("""
    SELECT
        reservation_id,
        booking_reference,
        room_id,
        checkin_date,
        checkout_date,
        booking_status
    FROM reservations
    WHERE booking_status = 'Checked-in'
""").fetchall()

print("\nCHECKED-IN RESERVATIONS:")

for reservation in reservations:
    print(dict(reservation))

connection.close()

connection.close()



    