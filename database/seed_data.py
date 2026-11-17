# ----------------------------------------
# 1. Import Database Connection
# ----------------------------------------

from database.db import get_db_connection


# ----------------------------------------
# 2. Insert Room Categories
# ----------------------------------------

def insert_room_categories():

    connection = get_db_connection()

    try:

        room_categories = [

            (
                "Standard Room",
                "Comfortable room with complimentary breakfast.",
                3000,
                1,
                2
            ),

            (
                "Deluxe Room",
                "Spacious room with additional comfort and complimentary breakfast.",
                4000,
                1,
                3
            ),

            (
                "Premium Sea-View Room",
                "Premium room offering a sea view and complimentary breakfast.",
                5000,
                1,
                3
            ),

            (
                "Family Suite",
                "Large suite suitable for families with complimentary breakfast.",
                8000,
                3,
                5
            )

        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO room_categories
            (
                category_name,
                description,
                base_price,
                minimum_guests,
                maximum_guests
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            room_categories
        )

        # ----------------------------------------
        # Update Premium Sea-View Room Capacity
        # ----------------------------------------

        connection.execute(
            """
            UPDATE room_categories
            SET minimum_guests = 2,
                maximum_guests = 5
            WHERE category_name = 'Premium Sea-View Room'
            """
        )

        # ----------------------------------------
        # Update Family Suite Capacity
        # ----------------------------------------

        connection.execute(
            """
            UPDATE room_categories
            SET minimum_guests = 3,
                maximum_guests = 8
            WHERE category_name = 'Family Suite'
            """
        )

        # ----------------------------------------
        # Update Deluxe Room Capacity
        # ----------------------------------------

        connection.execute(
            """
            UPDATE room_categories
            SET minimum_guests = 1,
            maximum_guests = 4
            WHERE category_name = 'Deluxe Room'
            """
        )

        connection.commit()

        print("Room categories inserted successfully!")

    finally:

        connection.close()


# ----------------------------------------
# 3. Run Room Category Insertion
# ----------------------------------------

if __name__ == "__main__":

    insert_room_categories()