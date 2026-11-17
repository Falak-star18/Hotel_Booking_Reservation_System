# ----------------------------------------
# 1. Import Database Connection
# ----------------------------------------

from database.db import get_db_connection


# ----------------------------------------
# 2. Update Seasonal Pricing Details
# ----------------------------------------

def update_seasons():

    connection = get_db_connection()

    try:

        # Update Peak Season
        connection.execute(
            """
            UPDATE seasons
            SET start_month = 11,
                end_month = 5,
                price_multiplier = 2.0,
                description = ?
            WHERE season_name = 'Peak Season'
            """,
            ("November to May - Double the base room price.",)
        )

        # Update Normal Season
        connection.execute(
            """
            UPDATE seasons
            SET start_month = 6,
                end_month = 10,
                price_multiplier = 1.0,
                description = ?
            WHERE season_name = 'Normal Season'
            """,
            ("June to October - Standard base room price.",)
        )

        connection.commit()

        print("Seasonal pricing updated successfully!")

    finally:

        connection.close()


# ----------------------------------------
# 3. Run Seasonal Pricing Update
# ----------------------------------------

if __name__ == "__main__":

    update_seasons()