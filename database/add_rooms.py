# ----------------------------------------
# 1. Import Database Connection
# ----------------------------------------

from database.db import get_db_connection


# ----------------------------------------
# 2. Insert Hotel Rooms
# ----------------------------------------

def insert_rooms():

    connection = get_db_connection()

    try:

        # Retrieve room categories
        categories = connection.execute(
            "SELECT category_id, category_name FROM room_categories"
        ).fetchall()

        # Create a dictionary for category IDs
        category_ids = {
            category["category_name"]: category["category_id"]
            for category in categories
        }

        rooms = []

        # ----------------------------------------
        # 3. Standard Rooms (101-110)
        # ----------------------------------------

        for room_number in range(101, 111):

            rooms.append(
                (str(room_number), category_ids["Standard Room"], 1)
            )

        # ----------------------------------------
        # 4. Deluxe Rooms (201-210)
        # ----------------------------------------

        for room_number in range(201, 211):

            rooms.append(
                (str(room_number), category_ids["Deluxe Room"], 2)
            )

        # ----------------------------------------
        # 5. Premium Sea-View Rooms (301-310)
        # ----------------------------------------

        for room_number in range(301, 311):

            rooms.append(
                (str(room_number), category_ids["Premium Sea-View Room"], 3)
            )

        # ----------------------------------------
        # 6. Family Suites (401-410)
        # ----------------------------------------

        for room_number in range(401, 411):

            rooms.append(
                (str(room_number), category_ids["Family Suite"], 4)
            )

        # ----------------------------------------
        # 7. Save Rooms in Database
        # ----------------------------------------

        connection.executemany(
            """
            INSERT OR IGNORE INTO rooms
            (room_number, category_id, floor_number)
            VALUES (?, ?, ?)
            """,
            rooms
        )

        connection.commit()

        print("Hotel rooms inserted successfully!")

    finally:

        connection.close()

# ----------------------------------------
# 8. Mark a Room as Clean/Ready
# ----------------------------------------

def mark_room_as_ready(room_number):

    connection = get_db_connection()

    try:
        connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Clean/Ready'
            WHERE room_number = ?
            """,
            (str(room_number),)
        )

        connection.commit()
        print(f"Room {room_number} marked as Clean/Ready!")

    finally:
        connection.close()


# ----------------------------------------
# 9. Create a Test Maintenance Report
# ----------------------------------------

def create_test_maintenance_report(room_number):

    connection = get_db_connection()

    try:
        connection.execute(
            """
            INSERT INTO maintenance_reports (
                room_id,
                reported_by,
                issue_description,
                maintenance_status
            )
            SELECT
                rooms.room_id,
                users.user_id,
                'Air conditioning not working - test report',
                'Reported'
            FROM rooms
            CROSS JOIN users
            WHERE rooms.room_number = ?
              AND users.role = 'Administrator'
            LIMIT 1
            """,
            (str(room_number),)
        )

        connection.commit()
        print(f"Test maintenance report created for Room {room_number}!")

    finally:
        connection.close()

# ----------------------------------------
# 10. Resolve a Maintenance Report
# ----------------------------------------

def resolve_maintenance_report(room_number):

    connection = get_db_connection()

    try:
        connection.execute(
            """
            UPDATE maintenance_reports
            SET maintenance_status = 'Resolved',
                resolved_at = CURRENT_TIMESTAMP
            WHERE room_id = (
                SELECT room_id
                FROM rooms
                WHERE room_number = ?
            )
            AND maintenance_status != 'Resolved'
            """,
            (str(room_number),)
        )

        connection.commit()
        print(f"Maintenance report for Room {room_number} resolved!")

    finally:
        connection.close()

# ----------------------------------------
# 10. Mark a Room as Dirty/Vacant
# ----------------------------------------

def mark_room_dirty(room_number):
    connection = get_db_connection()

    try:
        connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Dirty/Vacant'
            WHERE room_number = ?
            """,
            (str(room_number),)
        )

        connection.commit()
        print(f"Room {room_number} marked as Dirty/Vacant!")

    finally:
        connection.close()

# ----------------------------------------
# 11. Run Maintenance Resolution and Housekeeping Tests
# ----------------------------------------

if __name__ == "__main__":

    # Resolve the maintenance report for Room 106
    resolve_maintenance_report(106)

    # Mark Room 104 as clean and ready
    mark_room_as_ready(104)

    # Mark Room 104 as dirty
    mark_room_dirty(104)