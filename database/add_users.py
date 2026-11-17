# ----------------------------------------
# 1. Import Required Modules
# ----------------------------------------

import bcrypt

from database.db import get_db_connection
from getpass import getpass


# ----------------------------------------
# 2. Create Staff Account
# ----------------------------------------

def create_staff_account():

    connection = get_db_connection()

    try:

        # Get staff details
        full_name = input("Enter staff full name: ")
        email = input("Enter staff email: ")
        role = input(
            "Enter role (Administrator/Receptionist/Housekeeping Staff): "
        )

        # Get password securely
        password = getpass("Enter password: ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("Passwords do not match!")
            return

        if not full_name.strip() or not email.strip():
            print("Name and email cannot be empty!")
            return

        if role not in [
            "Administrator",
            "Receptionist",
            "Housekeeping Staff"
        ]:
            print("Invalid staff role!")
            return

        # Hash the password before storing it
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        # Insert staff account
        connection.execute(
            """
            INSERT INTO users
            (full_name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (full_name, email, password_hash, role)
        )

        connection.commit()

        print("Staff account created successfully!")

    except Exception as error:

        print("Unable to create staff account:", error)

    finally:

        connection.close()


# ----------------------------------------
# 3. Run Staff Account Creation
# ----------------------------------------

if __name__ == "__main__":

    create_staff_account()