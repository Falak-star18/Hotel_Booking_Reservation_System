
# ----------------------------------------
# 1. Import Required Modules
# ----------------------------------------

import sqlite3

from pathlib import Path


# ----------------------------------------
# 2. Define Database File Paths
# ----------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = BASE_DIR / "hotel.db"

SCHEMA_PATH = BASE_DIR / "schema.sql"


# ----------------------------------------
# 3. Initialize Database
# ----------------------------------------

def initialize_database():

    # Connect to the SQLite database
    connection = sqlite3.connect(DATABASE_PATH)

    try:

        # Enable foreign key constraints
        connection.execute("PRAGMA foreign_keys = ON")

        # Read SQL commands from schema.sql
        with open(SCHEMA_PATH, "r", encoding="utf-8") as file:

            schema = file.read()

        # Execute all table creation commands
        connection.executescript(schema)

        print("Database tables created successfully!")

    finally:

        connection.close()


# ----------------------------------------
# 4. Run Database Initialization
# ----------------------------------------

if __name__ == "__main__":

    initialize_database()
