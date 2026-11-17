# Test 1: Checks whether guests must log in before viewing their bookings.
def test_my_bookings_requires_guest_login(client):

    response = client.get(
        "/my-bookings",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert "/guest-login" in response.location

# Test 2: Checks whether a logged-in guest can access the My Bookings page.
def test_my_bookings_page_loads_for_logged_in_guest(client):

    with client.session_transaction() as session:
        session["guest_id"] = 1
        session["guest_name"] = "Test Guest"

    response = client.get("/my-bookings")

    assert response.status_code == 200

# Test 3: Checks whether a guest can see their own booking on the My Bookings page.
def test_my_bookings_displays_guest_booking(client, room_test_data):

    from app import get_db_connection

    connection = get_db_connection()

    # Get the sample room ID.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    # Create a sample guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Test Guest", "bookingtest@example.com", "9876543210")
    )

    guest_id = cursor.lastrowid

    # Create a sample reservation.
    connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "TEST-BOOKING-001", guest_id, room["room_id"],
            "2026-12-10", "2026-12-12", 2,
            "Confirmed", 9000, "Successful"
        )
    )

    connection.commit()
    connection.close()

    # Log in as the sample guest.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Test Guest"

    response = client.get("/my-bookings")

    assert response.status_code == 200
    assert b"TEST-BOOKING-001" in response.data

# Test 4: Checks whether a guest can see only their own bookings.
def test_my_bookings_shows_only_logged_in_guests_bookings(
    client, room_test_data
):

    from app import get_db_connection

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    # Create two different guests.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Guest One", "guestone@example.com", "9876543210")
    )
    guest_one_id = cursor.lastrowid

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Guest Two", "guesttwo@example.com", "9876543211")
    )
    guest_two_id = cursor.lastrowid

    # Create one booking for each guest.
    for guest_id, reference in [
        (guest_one_id, "GUEST-ONE-BOOKING"),
        (guest_two_id, "GUEST-TWO-BOOKING")
    ]:
        connection.execute(
            """
            INSERT INTO reservations (
                booking_reference, guest_id, room_id,
                checkin_date, checkout_date, number_of_guests,
                booking_status, total_amount, payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference, guest_id, room["room_id"],
                "2026-12-10", "2026-12-12", 2,
                "Confirmed", 9000, "Successful"
            )
        )

    connection.commit()
    connection.close()

    # Log in as Guest One.
    with client.session_transaction() as session:
        session["guest_id"] = guest_one_id
        session["guest_name"] = "Guest One"

    response = client.get("/my-bookings")

    assert response.status_code == 200
    assert b"GUEST-ONE-BOOKING" in response.data
    assert b"GUEST-TWO-BOOKING" not in response.data

# Test 5: Checks whether guests must log in before cancelling a booking.
def test_cancel_booking_requires_guest_login(client):

    response = client.post(
        "/cancel-booking/1",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert "/guest-login" in response.location

# Test 6: Checks whether a guest is prevented from cancelling another guest's booking.
def test_guest_cannot_cancel_another_guests_booking(
    client, room_test_data
):

    from app import get_db_connection

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    # Create two guests.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Booking Owner", "owner@example.com", "9876543210")
    )
    owner_id = cursor.lastrowid

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Other Guest", "other@example.com", "9876543211")
    )
    other_guest_id = cursor.lastrowid

    # Create a confirmed booking for the first guest.
    cursor = connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "OWNER-BOOKING-001", owner_id, room["room_id"],
            "2026-12-10", "2026-12-12", 2,
            "Confirmed", 9000, "Successful"
        )
    )

    reservation_id = cursor.lastrowid

    # Create a successful payment for the booking.
    connection.execute(
        """
        INSERT INTO payments (
            reservation_id, payment_reference,
            payment_method, payment_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id, "PAY-OWNER-001",
            "UPI", 9000, "Successful"
        )
    )

    connection.commit()
    connection.close()

    # Log in as the other guest, not the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = other_guest_id
        session["guest_name"] = "Other Guest"

    response = client.post(
        f"/cancel-booking/{reservation_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify that the original booking was not cancelled.
    connection = get_db_connection()

    booking = connection.execute(
    """
    SELECT booking_status
    FROM reservations
    WHERE reservation_id = ?
    """,
    (reservation_id,)
    ).fetchone()

    refund = connection.execute(
    """
    SELECT refund_id
    FROM refunds
    WHERE reservation_id = ?
    """,
    (reservation_id,)
    ).fetchone()

    connection.close()

    assert booking["booking_status"] == "Confirmed"
    assert refund is None

# Test 7: Checks whether cancelling at least 72 hours before check-in gives a full refund.
def test_cancel_booking_with_100_percent_refund(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    # Create a guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Refund Guest", "refundtest@example.com", "9876543210")
    )
    guest_id = cursor.lastrowid

    # Set check-in four days from today.
    checkin_date = (
        datetime.now() + timedelta(days=4)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=6)
    ).strftime("%Y-%m-%d")

    # Create a confirmed reservation.
    cursor = connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "FULL-REFUND-001", guest_id, room["room_id"],
            checkin_date, checkout_date, 2,
            "Confirmed", 9000, "Successful"
        )
    )
    reservation_id = cursor.lastrowid

    # Create a successful payment.
    cursor = connection.execute(
        """
        INSERT INTO payments (
            reservation_id, payment_reference,
            payment_method, payment_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id, "PAY-FULL-REFUND-001",
            "UPI", 9000, "Successful"
        )
    )

    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Refund Guest"

    # Cancel the booking.
    response = client.post(
        f"/cancel-booking/{reservation_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Check the updated booking, payment and refund records.
    connection = get_db_connection()

    booking = connection.execute(
        "SELECT booking_status, payment_status FROM reservations WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    payment = connection.execute(
        "SELECT payment_status FROM payments WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    refund = connection.execute(
        "SELECT refund_percentage, refund_amount, refund_status FROM refunds WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    connection.close()

    assert booking["booking_status"] == "Cancelled"
    assert booking["payment_status"] == "Refunded"
    assert payment["payment_status"] == "Refunded"
    assert refund["refund_percentage"] == 100
    assert refund["refund_amount"] == 9000
    assert refund["refund_status"] == "Processed"

# Test 8: Checks whether cancelling between 48 and 72 hours before check-in gives a 50% refund.
def test_cancel_booking_with_50_percent_refund(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    # Create a guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Partial Refund Guest", "partialrefund@example.com", "9876543211")
    )
    guest_id = cursor.lastrowid

    # Set check-in three days from today.
    checkin_date = (
        datetime.now() + timedelta(days=2)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=4)
    ).strftime("%Y-%m-%d")

    # Create a confirmed reservation.
    cursor = connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "PARTIAL-REFUND-001", guest_id, room["room_id"],
            checkin_date, checkout_date, 2,
            "Confirmed", 9000, "Successful"
        )
    )
    reservation_id = cursor.lastrowid

    # Create a successful payment.
    cursor.execute(
        """
        INSERT INTO payments (
            reservation_id, payment_reference,
            payment_method, payment_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id, "PAY-PARTIAL-REFUND-001",
            "UPI", 9000, "Successful"
        )
    )

    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Partial Refund Guest"

    # Cancel the booking.
    response = client.post(
        f"/cancel-booking/{reservation_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify the booking, payment and refund records.
    connection = get_db_connection()

    booking = connection.execute(
        "SELECT booking_status, payment_status FROM reservations WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    payment = connection.execute(
        "SELECT payment_status FROM payments WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    refund = connection.execute(
        "SELECT refund_percentage, refund_amount, refund_status FROM refunds WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    connection.close()

    assert booking["booking_status"] == "Cancelled"
    assert booking["payment_status"] == "Partially Refunded"
    assert payment["payment_status"] == "Partially Refunded"
    assert refund["refund_percentage"] == 50
    assert refund["refund_amount"] == 4500
    assert refund["refund_status"] == "Processed"

# Test 9: Checks whether cancelling one day before check-in gives no refund.
def test_cancel_booking_with_no_refund(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("No Refund Guest", "norefund@example.com", "9876543212")
    )
    guest_id = cursor.lastrowid

    # Set check-in one day from today.
    checkin_date = (
        datetime.now() + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=3)
    ).strftime("%Y-%m-%d")

    cursor = connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "NO-REFUND-001", guest_id, room["room_id"],
            checkin_date, checkout_date, 2,
            "Confirmed", 9000, "Successful"
        )
    )
    reservation_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO payments (
            reservation_id, payment_reference,
            payment_method, payment_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id, "PAY-NO-REFUND-001",
            "UPI", 9000, "Successful"
        )
    )

    connection.commit()
    connection.close()

    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "No Refund Guest"

    response = client.post(
        f"/cancel-booking/{reservation_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify booking, payment and refund details.
    connection = get_db_connection()

    booking = connection.execute(
        "SELECT booking_status, payment_status FROM reservations WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    payment = connection.execute(
        "SELECT payment_status FROM payments WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    refund = connection.execute(
        "SELECT refund_percentage, refund_amount, refund_status FROM refunds WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    connection.close()

    assert booking["booking_status"] == "Cancelled"
    assert booking["payment_status"] == "No Refund"
    assert payment["payment_status"] == "No Refund"
    assert refund["refund_percentage"] == 0
    assert refund["refund_amount"] == 0
    assert refund["refund_status"] == "Not Eligible"

# Test 10: Checks that a guest cannot cancel a booking on the check-in date.
def test_cannot_cancel_booking_on_checkin_date(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Checkin Guest", "checkinguest@example.com", "9876543213")
    )
    guest_id = cursor.lastrowid

    # Set check-in date to today.
    checkin_date = datetime.now().strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=2)
    ).strftime("%Y-%m-%d")

    cursor = connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "CHECKIN-DATE-001", guest_id, room["room_id"],
            checkin_date, checkout_date, 2,
            "Confirmed", 9000, "Successful"
        )
    )
    reservation_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO payments (
            reservation_id, payment_reference,
            payment_method, payment_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id, "PAY-CHECKIN-DATE-001",
            "UPI", 9000, "Successful"
        )
    )

    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Checkin Guest"

    response = client.post(
        f"/cancel-booking/{reservation_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify that the booking and payment remain unchanged.
    connection = get_db_connection()

    booking = connection.execute(
        "SELECT booking_status, payment_status FROM reservations WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    payment = connection.execute(
        "SELECT payment_status FROM payments WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    refund = connection.execute(
        "SELECT refund_id FROM refunds WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    connection.close()

    assert booking["booking_status"] == "Confirmed"
    assert booking["payment_status"] == "Successful"
    assert payment["payment_status"] == "Successful"
    assert refund is None

# Test 11: Checks that an already-cancelled booking cannot be cancelled again.
def test_cannot_cancel_already_cancelled_booking(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Already Cancelled Guest", "alreadycancelled@example.com", "9876543214")
    )
    guest_id = cursor.lastrowid

    checkin_date = (
        datetime.now() + timedelta(days=5)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=7)
    ).strftime("%Y-%m-%d")

    # Create a booking that is already cancelled.
    cursor = connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "ALREADY-CANCELLED-001", guest_id, room["room_id"],
            checkin_date, checkout_date, 2,
            "Cancelled", 9000, "Refunded"
        )
    )
    reservation_id = cursor.lastrowid

    # Create its successful payment.
    cursor.execute(
        """
        INSERT INTO payments (
            reservation_id, payment_reference,
            payment_method, payment_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id, "PAY-ALREADY-CANCELLED-001",
            "UPI", 9000, "Successful"
        )
    )
    payment_id = cursor.lastrowid

    # Insert the original refund record.
    cursor.execute(
        """
        INSERT INTO refunds (
            payment_id, reservation_id, cancellation_time,
            refund_percentage, refund_amount, refund_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payment_id, reservation_id,
            datetime.now().isoformat(timespec="seconds"),
            100, 9000, "Processed"
        )
    )

    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Already Cancelled Guest"

    # Try to cancel the same booking again.
    response = client.post(
        f"/cancel-booking/{reservation_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify that no duplicate refund was created.
    connection = get_db_connection()

    booking = connection.execute(
        "SELECT booking_status FROM reservations WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    refunds = connection.execute(
        "SELECT COUNT(*) AS refund_count FROM refunds WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    connection.close()

    assert booking["booking_status"] == "Cancelled"
    assert refunds["refund_count"] == 1

# Test 12: Checks that a booking cannot be cancelled without successful payment.
def test_cannot_cancel_booking_without_successful_payment(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Pending Payment Guest", "pendingpayment@example.com", "9876543215")
    )
    guest_id = cursor.lastrowid

    checkin_date = (
        datetime.now() + timedelta(days=5)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=7)
    ).strftime("%Y-%m-%d")

    # Create a confirmed booking with pending payment.
    cursor = connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "PENDING-PAYMENT-001", guest_id, room["room_id"],
            checkin_date, checkout_date, 2,
            "Confirmed", 9000, "Pending"
        )
    )
    reservation_id = cursor.lastrowid

    # Create a pending payment.
    cursor.execute(
        """
        INSERT INTO payments (
            reservation_id, payment_reference,
            payment_method, payment_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id, "PAY-PENDING-001",
            "UPI", 9000, "Pending"
        )
    )

    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Pending Payment Guest"

    # Attempt to cancel the booking.
    response = client.post(
        f"/cancel-booking/{reservation_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify that the booking and payment remain unchanged.
    connection = get_db_connection()

    booking = connection.execute(
        "SELECT booking_status, payment_status FROM reservations WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    payment = connection.execute(
        "SELECT payment_status FROM payments WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    refund = connection.execute(
        "SELECT refund_id FROM refunds WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    connection.close()

    assert booking["booking_status"] == "Confirmed"
    assert booking["payment_status"] == "Pending"
    assert payment["payment_status"] == "Pending"
    assert refund is None

# Test 13: Checks that cancelling a non-existent booking is handled safely.
def test_cancel_booking_not_found(client):

    # Log in as a guest.
    with client.session_transaction() as session:
        session["guest_id"] = 1
        session["guest_name"] = "Test Guest"

    # Attempt to cancel a booking with a non-existent reservation ID.
    response = client.post(
        "/cancel-booking/99999",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify that no refund record was created.
    from app import get_db_connection

    connection = get_db_connection()

    refund_count = connection.execute(
        "SELECT COUNT(*) FROM refunds"
    ).fetchone()[0]

    connection.close()

    assert refund_count == 0

# Test 14: Checks that a guest cannot cancel a booking that is already checked in.
def test_cannot_cancel_checked_in_booking(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Checked In Guest", "checkedinguest@example.com", "9876543216")
    )
    guest_id = cursor.lastrowid

    checkin_date = (
        datetime.now() + timedelta(days=5)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=7)
    ).strftime("%Y-%m-%d")

    # Create a booking with Checked-in status.
    cursor = connection.execute(
        """
        INSERT INTO reservations (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            booking_status, total_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "CHECKED-IN-001", guest_id, room["room_id"],
            checkin_date, checkout_date, 2,
            "Checked-in", 9000, "Successful"
        )
    )
    reservation_id = cursor.lastrowid

    # Create a successful payment.
    cursor.execute(
        """
        INSERT INTO payments (
            reservation_id, payment_reference,
            payment_method, payment_amount, payment_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id, "PAY-CHECKED-IN-001",
            "UPI", 9000, "Successful"
        )
    )

    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Checked In Guest"

    # Attempt to cancel the checked-in booking.
    response = client.post(
        f"/cancel-booking/{reservation_id}",
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify that the booking, payment and refund remain unchanged.
    connection = get_db_connection()

    booking = connection.execute(
        "SELECT booking_status, payment_status FROM reservations WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    payment = connection.execute(
        "SELECT payment_status FROM payments WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    refund = connection.execute(
        "SELECT refund_id FROM refunds WHERE reservation_id = ?",
        (reservation_id,)
    ).fetchone()

    connection.close()

    assert booking["booking_status"] == "Checked-in"
    assert booking["payment_status"] == "Successful"
    assert payment["payment_status"] == "Successful"
    assert refund is None