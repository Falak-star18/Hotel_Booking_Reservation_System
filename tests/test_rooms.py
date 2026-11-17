# Test 1: Checks whether a guest who is not logged in is redirected to the guest login page.
def test_check_availability_requires_guest_login(client):

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": "1"
        },
        follow_redirects=False
    )

    assert response.status_code == 302
    assert "/guest-login" in response.location

# Test 2: Checks whether a logged-in guest can successfully view available rooms.
def test_check_availability_success(client, room_test_data):

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert b"Rooms Available!" in response.data

# Test 3: Checks whether availability search rejects guests below the minimum room capacity.
def test_check_availability_below_minimum_guests(client, room_test_data):

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "0",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 400
    assert b"requires at least 1 guests" in response.data

# Test 4: Checks whether availability search rejects guests above the maximum room capacity.
def test_check_availability_above_maximum_guests(client, room_test_data):

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "5",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 400
    assert b"allows a maximum of 4 guests" in response.data

# Test 5: Checks whether availability search rejects an invalid room category.
def test_check_availability_invalid_category(client):

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": "999"
        }
    )

    assert response.status_code == 400
    assert b"Invalid room category selected!" in response.data

# Test 6: Checks whether rooms that are not clean and ready are excluded from availability.
def test_check_availability_excludes_dirty_room(client, room_test_data):

    from app import get_db_connection

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE rooms
        SET housekeeping_status = 'Dirty/Vacant'
        WHERE room_number = ?
        """,
        (room_test_data["room_number"],)
    )

    connection.commit()
    connection.close()

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert b"TEST-101" not in response.data

# Test 7: Checks whether rooms under maintenance are excluded from availability.
def test_check_availability_excludes_maintenance_room(client, room_test_data):

    from app import get_db_connection

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE rooms
        SET maintenance_status = 'Under Maintenance'
        WHERE room_number = ?
        """,
        (room_test_data["room_number"],)
    )

    connection.commit()
    connection.close()

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert b"TEST-101" not in response.data

# Test 8: Checks whether inactive rooms are excluded from availability.
def test_check_availability_excludes_inactive_room(client, room_test_data):

    from app import get_db_connection

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE rooms
        SET is_active = 0
        WHERE room_number = ?
        """,
        (room_test_data["room_number"],)
    )

    connection.commit()
    connection.close()

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert b"TEST-101" not in response.data

# Test 9: Checks whether rooms with overlapping confirmed reservations are excluded from availability.
def test_check_availability_excludes_reserved_room(client, room_test_data):

    from app import get_db_connection

    connection = get_db_connection()

    # Insert a test guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        ("Test Guest", "reservation_test@example.com", "9876543210", "test_hash")
    )

    guest_id = cursor.lastrowid

    # Insert an existing confirmed reservation for the sample room.
    connection.execute(
        """
        INSERT INTO reservations
        (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date,
            number_of_guests, booking_status,
            total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "TEST-BOOKING-001",
            guest_id,
            1,
            "2026-11-10",
            "2026-11-12",
            2,
            "Confirmed",
            6000,
            "Successful"
        )
    )

    connection.commit()
    connection.close()

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert b"TEST-101" not in response.data

# Test 10: Checks whether rooms with unresolved maintenance reports are excluded from availability.
def test_check_availability_excludes_unresolved_maintenance(client, room_test_data):

    from app import get_db_connection

    connection = get_db_connection()

    # Insert a test user who reports the maintenance issue.
    cursor = connection.execute(
        """
        INSERT INTO users (full_name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        ("Test Maintenance User", "maintenance_test@example.com", "test_hash", "Administrator")
    )

    user_id = cursor.lastrowid

    # Insert an unresolved maintenance report for the sample room.
    connection.execute(
        """
        INSERT INTO maintenance_reports
        (room_id, reported_by, issue_description, maintenance_status)
        VALUES (?, ?, ?, ?)
        """,
        (
            1,
            user_id,
            "Air conditioning not working",
            "Reported"
        )
    )

    connection.commit()
    connection.close()

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert b"TEST-101" not in response.data

# Test 11: Checks whether the correct total room price is calculated during Peak Season.
def test_check_availability_peak_season_pricing(client, room_test_data):

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert "₹9,000.00".encode("utf-8") in response.data

# Test 12: Checks whether the correct total room price is calculated during Normal Season.
def test_check_availability_normal_season_pricing(client, room_test_data):

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-07-10",
            "checkout_date": "2026-07-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert "₹6,000.00".encode("utf-8") in response.data

# Test 13: Checks whether rooms with active booking holds are excluded from availability.
def test_check_availability_excludes_active_hold(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    # Insert a test guest for the room hold.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        ("Hold Test Guest", "hold_test@example.com", "9876543211", "test_hash")
    )

    guest_id = cursor.lastrowid

    # Create a room hold that expires one hour from now.
    hold_expiry = (datetime.now() + timedelta(hours=1)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    connection.execute(
        """
        INSERT INTO room_holds
        (room_id, guest_id, checkin_date, checkout_date, hold_expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            1,
            guest_id,
            "2026-11-10",
            "2026-11-12",
            hold_expiry
        )
    )

    connection.commit()
    connection.close()

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert b"TEST-101" not in response.data

# Test 14: Checks whether a room becomes available again after its temporary hold expires.
def test_check_availability_expired_hold_releases_room(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    # Insert a test guest for the room hold.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        ("Expired Hold Guest", "expired_hold@example.com", "9876543212", "test_hash")
    )

    guest_id = cursor.lastrowid

    # Create a room hold that expired one hour ago.
    hold_expiry = (datetime.now() - timedelta(hours=1)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    connection.execute(
        """
        INSERT INTO room_holds
        (room_id, guest_id, checkin_date, checkout_date, hold_expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            1,
            guest_id,
            "2026-11-10",
            "2026-11-12",
            hold_expiry
        )
    )

    connection.commit()
    connection.close()

    with client.session_transaction() as session:
        session["guest_id"] = 1

    response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert response.status_code == 200
    assert b"Rooms Available!" in response.data

    # Verify that the expired hold was deleted.
    connection = get_db_connection()

    remaining_holds = connection.execute(
        "SELECT COUNT(*) FROM room_holds WHERE room_id = ?",
        (1,)
    ).fetchone()[0]

    connection.close()

    assert remaining_holds == 0