
# ----------------------------------------
# 1. Import Database Connection
# ----------------------------------------

from database.db import get_db_connection


# ----------------------------------------
# 2. Connect to Database
# ----------------------------------------

connection = get_db_connection()

# Add password_hash column if it does not exist

columns = connection.execute(
    "PRAGMA table_info(guests)"
).fetchall()

column_names = [column["name"] for column in columns]

if "password_hash" not in column_names:
    connection.execute(
        "ALTER TABLE guests ADD COLUMN password_hash TEXT"
    )
    connection.commit()
    print("\nGuest password_hash column added successfully.")
else:
    print("\nGuest password_hash column already exists.")

# Check for duplicate guest email addresses

duplicates = connection.execute(
    """
    SELECT email, COUNT(*) AS total
    FROM guests
    WHERE email IS NOT NULL AND email != ''
    GROUP BY email
    HAVING COUNT(*) > 1
    """
).fetchall()

print("\nDuplicate Guest Emails:")

if duplicates:
    for duplicate in duplicates:
        print(duplicate["email"], "-", duplicate["total"], "records")
else:
    print("No duplicate guest emails found.")

# Enforce unique guest email addresses

connection.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS
    idx_guests_unique_email
    ON guests(email)
    """
)

connection.commit()

print("\nUnique guest email index created successfully.")

# ----------------------------------------
# 3. Retrieve All Database Tables
# ----------------------------------------

tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type = 'table' "
    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
).fetchall()


# ----------------------------------------
# 4. Display Table Information
# ----------------------------------------

print("Total tables:", len(tables))

print("\nDatabase Tables:")

for table in tables:
    print("-", table["name"])

    # ----------------------------------------
# Display Guest Table Structure
# ----------------------------------------

guest_columns = connection.execute(
    "PRAGMA table_info(guests)"
).fetchall()

print("\nGuest Table Structure:")

for column in guest_columns:
    print(
        "Column:", column["name"],
        "| Type:", column["type"],
        "| Not Null:", column["notnull"],
        "| Primary Key:", column["pk"]
    )

# Check existing guest email addresses

guest_emails = connection.execute(
    "SELECT guest_id, full_name, email FROM guests"
).fetchall()

print("\nExisting Guest Records:")

for guest in guest_emails:
    print(
        "ID:", guest["guest_id"],
        "| Name:", guest["full_name"],
        "| Email:", guest["email"]
    )

# ----------------------------------------
# 6. Display Room Categories
# ----------------------------------------

categories = connection.execute(
    "SELECT * FROM room_categories"
).fetchall()

print("\nRoom Categories:")

for category in categories:

    print(
        category["category_name"],
        "- ₹",
        category["base_price"],
        "- Capacity:",
        category["minimum_guests"],
        "to",
        category["maximum_guests"],
        "guests"
    )

# ----------------------------------------
# 7. Display All Hotel Rooms
# ----------------------------------------

rooms = connection.execute(
    """
    SELECT
        rooms.room_number,
        room_categories.category_name,
        rooms.floor_number,
        rooms.housekeeping_status,
        rooms.maintenance_status
    FROM rooms
    JOIN room_categories
    ON rooms.category_id = room_categories.category_id
    ORDER BY rooms.room_number
    """
).fetchall()

print("\nTotal Hotel Rooms:", len(rooms))

print("\nHotel Room Details:")

for room in rooms:

    print(
        "Room:", room["room_number"],
        "| Category:", room["category_name"],
        "| Floor:", room["floor_number"],
        "| Housekeeping:", room["housekeeping_status"],
        "| Maintenance:", room["maintenance_status"]
    )

# ----------------------------------------
# 8. Display Seasonal Pricing Details
# ----------------------------------------

seasons = connection.execute(
    "SELECT * FROM seasons ORDER BY season_id"
).fetchall()

print("\nSeasonal Pricing Details:")

for season in seasons:

    print(
        "Season:", season["season_name"],
        "| Start Month:", season["start_month"],
        "| End Month:", season["end_month"],
        "| Multiplier:", season["price_multiplier"],
        "x"
    )

# ----------------------------------------
# 9. Display Staff Accounts
# ----------------------------------------

users = connection.execute(
    """
    SELECT user_id, full_name, email, role, created_at
    FROM users
    """
).fetchall()

print("\nStaff Accounts:")

for user in users:

    print(
        "ID:", user["user_id"],
        "| Name:", user["full_name"],
        "| Email:", user["email"],
        "| Role:", user["role"]
    )

# ----------------------------------------
# 10. Display Database Record Summary
# ----------------------------------------

print("\nDatabase Record Summary:")

tables = [
    "users",
    "guests",
    "room_categories",
    "rooms",
    "reservations",
    "reservation_occupants",
    "seasons",
    "reservation_nightly_rates",
    "housekeeping_assignments",
    "maintenance_reports",
    "booking_documents"
]

for table in tables:

    result = connection.execute(
        f"SELECT COUNT(*) AS total FROM {table}"
    ).fetchone()

    print(table, ":", result["total"], "records")

# ----------------------------------------
# 11. Diagnose Room Availability for Today
# ----------------------------------------

from datetime import date

today = date.today().isoformat()

available_rooms = connection.execute(
    """
    SELECT room_number
    FROM rooms
    WHERE is_active = 1
      AND housekeeping_status = 'Clean/Ready'
      AND maintenance_status = 'Operational'

      AND NOT EXISTS (
          SELECT 1
          FROM reservations
          WHERE reservations.room_id = rooms.room_id
            AND reservations.booking_status IN ('Confirmed', 'Checked-in')
            AND reservations.checkin_date < ?
            AND reservations.checkout_date > ?
      )

      AND NOT EXISTS (
          SELECT 1
          FROM maintenance_reports
          WHERE maintenance_reports.room_id = rooms.room_id
            AND maintenance_reports.maintenance_status != 'Resolved'
      )

    ORDER BY room_number
    """,
    (today, today)
).fetchall()

print("\nRoom Availability Diagnostic:")
print("Today's date:", today)
print("Available rooms:", len(available_rooms))

for room in available_rooms:
    print("Available:", room["room_number"])

# Verify payments table
payments_table = connection.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    AND name = 'payments'
    """
).fetchone()

if payments_table:
    print("Payments table: EXISTS")
else:
    print("Payments table: NOT FOUND")

# Verify payment and refund tables
for table_name in ["payments", "refunds"]:
    result = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,)
    ).fetchone()

    print(f"{table_name} table:", "EXISTS" if result else "NOT FOUND")


# Verify payment_status column
columns = connection.execute(
    "PRAGMA table_info(reservations)"
).fetchall()

column_names = [column["name"] for column in columns]

print(
    "payment_status column:",
    "EXISTS" if "payment_status" in column_names else "NOT FOUND"
)
    
# ----------------------------------------
# 5. Close Database Connection
# ----------------------------------------

connection.close()
