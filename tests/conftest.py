import pytest
import tempfile
import os
import sqlite3
from pathlib import Path

import app as flask_app


@pytest.fixture
def app():
    # Create a temporary test database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Connect to the temporary database
    connection = sqlite3.connect(db_path)

    # Enable foreign key constraints
    connection.execute("PRAGMA foreign_keys = ON")

    # Load the existing database schema
    schema_path = (
        Path(__file__).resolve().parent.parent
        / "database"
        / "schema.sql"
    )

    with open(schema_path, "r", encoding="utf-8") as schema_file:
        connection.executescript(schema_file.read())

    connection.close()

    # Redirect application database connections
    original_get_db_connection = flask_app.get_db_connection

    def get_test_db_connection():
        connection = sqlite3.connect(db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    flask_app.get_db_connection = get_test_db_connection

    flask_app.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key"
    )

    yield flask_app.app

    # Restore original connection function
    flask_app.get_db_connection = original_get_db_connection

    # Delete temporary database
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()

# Provides sample room and seasonal pricing data for room availability tests.
@pytest.fixture
def room_test_data(app):
    from app import get_db_connection

    connection = get_db_connection()

    # Insert a sample room category.
    cursor = connection.execute(
        """
        INSERT INTO room_categories
        (category_name, description, base_price, minimum_guests, maximum_guests)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Deluxe Room", "Test room category", 3000, 1, 4)
    )

    category_id = cursor.lastrowid

    # Insert a clean, operational and active room.
    cursor.execute(
        """
        INSERT INTO rooms
        (room_number, category_id, floor_number,
         housekeeping_status, maintenance_status, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("TEST-101", category_id, 1, "Clean/Ready", "Operational", 1)
    )

    # Insert seasonal pricing records.
    cursor.execute(
        """
        INSERT INTO seasons
        (season_name, start_month, end_month, price_multiplier)
        VALUES (?, ?, ?, ?)
        """,
        ("Peak Season", 11, 5, 1.5)
    )

    cursor.execute(
        """
        INSERT INTO seasons
        (season_name, start_month, end_month, price_multiplier)
        VALUES (?, ?, ?, ?)
        """,
        ("Normal Season", 6, 10, 1.0)
    )

    connection.commit()

    data = {
        "category_id": category_id,
        "room_number": "TEST-101"
    }

    connection.close()

    return data

