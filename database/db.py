# ----------------------------------------
# 1. Import SQLite
# ----------------------------------------

import sqlite3

# ----------------------------------------
# 2. Import Path
# ----------------------------------------

from pathlib import Path

# ----------------------------------------
# 3. Define Database File Location
# ----------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = BASE_DIR / "database" / "hotel.db"

# ----------------------------------------
# 4. Create Database Connection Function
# ----------------------------------------

def get_db_connection():

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    # Return database rows as dictionary-like objects
    connection.row_factory = sqlite3.Row

    return connection
