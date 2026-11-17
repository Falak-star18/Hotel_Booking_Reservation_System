# Test 1: Tests that successful payment creates a confirmed reservation.
def test_successful_payment_creates_reservation(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create a test guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Payment Test Guest", "paymenttest@example.com", "9876543217")
    )
    guest_id = cursor.lastrowid

    # Get the test room.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    # Prepare booking details.
    checkin_date = (
        datetime.now() + timedelta(days=10)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=12)
    ).strftime("%Y-%m-%d")

    booking_data = {
        "base_price": 3000,
        "occupants": [
            {"occupant_name": "Payment Test Guest", "age": 25}
        ],
        "nightly_rates": [
            {
                "stay_date": checkin_date,
                "nightly_price": 4500,
                "season_multiplier": 1.5
            },
            {
                "stay_date": (
                    datetime.strptime(checkin_date, "%Y-%m-%d")
                    + timedelta(days=1)
                ).strftime("%Y-%m-%d"),
                "nightly_price": 4500,
                "season_multiplier": 1.5
            }
        ]
    }

    # Create a pending booking.
    cursor = connection.execute(
        """
        INSERT INTO pending_bookings (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            total_amount, booking_data, expires_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "PAYMENT-TEST-001",
            guest_id,
            room["room_id"],
            checkin_date,
            checkout_date,
            1,
            9000,
            json.dumps(booking_data),
            (datetime.now() + timedelta(minutes=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Pending"
        )
    )

    pending_booking_id = cursor.lastrowid

    # Create a room hold.
    connection.execute(
        """
        INSERT INTO room_holds (
            room_id, guest_id, checkin_date,
            checkout_date, hold_expires_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            room["room_id"],
            guest_id,
            checkin_date,
            checkout_date,
            (datetime.now() + timedelta(minutes=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )

    connection.commit()
    connection.close()

    # Log in as the guest.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Payment Test Guest"

    # Process a successful payment.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Successful"}
    )

    assert response.status_code == 302
    assert "/payment-success/" in response.headers["Location"]

    # Verify the database records.
    connection = get_db_connection()

    reservation = connection.execute(
        """
        SELECT reservation_id, booking_status, payment_status, total_amount
        FROM reservations
        WHERE booking_reference = ?
        """,
        ("PAYMENT-TEST-001",)
    ).fetchone()

    payment = connection.execute(
        """
        SELECT payment_status, payment_amount
        FROM payments
        WHERE reservation_id = ?
        """,
        (reservation["reservation_id"],)
    ).fetchone()

    pending_booking = connection.execute(
        """
        SELECT status FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    room_hold = connection.execute(
        """
        SELECT hold_id FROM room_holds
        WHERE guest_id = ?
        """,
        (guest_id,)
    ).fetchone()

    connection.close()

    assert reservation["booking_status"] == "Confirmed"
    assert reservation["payment_status"] == "Successful"
    assert reservation["total_amount"] == 9000

    assert payment["payment_status"] == "Successful"
    assert payment["payment_amount"] == 9000

    assert pending_booking["status"] == "Completed"
    assert room_hold is None

# Test 2: Tests that failed payment does not create a reservation.
def test_failed_payment_does_not_create_reservation(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create a test guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Failed Payment Guest", "failedpayment@example.com", "9876543218")
    )
    guest_id = cursor.lastrowid

    # Get the test room.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin_date = (
        datetime.now() + timedelta(days=10)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=12)
    ).strftime("%Y-%m-%d")

    booking_data = {
        "base_price": 3000,
        "occupants": [
            {"occupant_name": "Failed Payment Guest", "age": 25}
        ],
        "nightly_rates": []
    }

    # Create a pending booking.
    cursor = connection.execute(
        """
        INSERT INTO pending_bookings (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            total_amount, booking_data, expires_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "FAILED-PAYMENT-001",
            guest_id,
            room["room_id"],
            checkin_date,
            checkout_date,
            1,
            9000,
            json.dumps(booking_data),
            (datetime.now() + timedelta(minutes=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Pending"
        )
    )

    pending_booking_id = cursor.lastrowid

    # Create a room hold.
    connection.execute(
        """
        INSERT INTO room_holds (
            room_id, guest_id, checkin_date,
            checkout_date, hold_expires_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            room["room_id"],
            guest_id,
            checkin_date,
            checkout_date,
            (datetime.now() + timedelta(minutes=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )

    connection.commit()
    connection.close()

    # Log in as the guest.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Failed Payment Guest"

    # Process a failed payment.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Failed"}
    )

    assert response.status_code == 200
    assert b"payment" in response.data.lower()

    # Verify the database records.
    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT status FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    payment_attempt = connection.execute(
        """
        SELECT payment_status, payment_amount
        FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    reservation = connection.execute(
        """
        SELECT reservation_id FROM reservations
        WHERE booking_reference = ?
        """,
        ("FAILED-PAYMENT-001",)
    ).fetchone()

    room_hold = connection.execute(
        """
        SELECT hold_id FROM room_holds
        WHERE guest_id = ?
        """,
        (guest_id,)
    ).fetchone()

    payment = connection.execute(
        """
        SELECT payment_id FROM payments
        WHERE payment_reference IN (
            SELECT payment_reference
            FROM payment_attempts
            WHERE pending_booking_id = ?
        )
        """,
        (pending_booking_id,)
    ).fetchone()

    connection.close()

    assert pending_booking["status"] == "Failed"
    assert payment_attempt["payment_status"] == "Failed"
    assert payment_attempt["payment_amount"] == 9000
    assert reservation is None
    assert room_hold is None
    assert payment is None

# Test 3: Tests that guests must log in before processing payment.
def test_process_payment_requires_guest_login(client):

    # Attempt payment without logging in.
    response = client.post(
        "/process-payment/1",
        data={"payment_result": "Successful"},
        follow_redirects=False
    )

    # Verify redirection to the guest login page.
    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 4: Tests that invalid payment selections are rejected.
def test_invalid_payment_selection(client):

    # Log in as a guest.
    with client.session_transaction() as session:
        session["guest_id"] = 1
        session["guest_name"] = "Test Guest"

    # Submit an invalid payment result.
    response = client.post(
        "/process-payment/1",
        data={"payment_result": "Invalid"},
        follow_redirects=False
    )

    # Verify redirection to the payment page.
    assert response.status_code == 302
    assert "/payment/1" in response.headers["Location"]

# Test 5: Tests that expired payment windows cannot be processed.
def test_expired_payment_window(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create a test guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Expired Payment Guest", "expiredpayment@example.com", "9876543219")
    )
    guest_id = cursor.lastrowid

    # Get the test room.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin_date = (
        datetime.now() + timedelta(days=10)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=12)
    ).strftime("%Y-%m-%d")

    booking_data = {
        "base_price": 3000,
        "occupants": [],
        "nightly_rates": []
    }

    # Create a pending booking with an expired payment window.
    cursor = connection.execute(
        """
        INSERT INTO pending_bookings (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            total_amount, booking_data, expires_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "EXPIRED-PAYMENT-001",
            guest_id,
            room["room_id"],
            checkin_date,
            checkout_date,
            1,
            9000,
            json.dumps(booking_data),
            (datetime.now() - timedelta(minutes=5)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Pending"
        )
    )

    pending_booking_id = cursor.lastrowid

    # Create an associated room hold.
    connection.execute(
        """
        INSERT INTO room_holds (
            room_id, guest_id, checkin_date,
            checkout_date, hold_expires_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            room["room_id"],
            guest_id,
            checkin_date,
            checkout_date,
            (datetime.now() + timedelta(minutes=5)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )

    connection.commit()
    connection.close()

    # Log in as the guest.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Expired Payment Guest"

    # Attempt payment after the expiry time.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Successful"}
    )

    assert response.status_code == 302

    # Verify the booking and room hold.
    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT status FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    room_hold = connection.execute(
        """
        SELECT hold_id FROM room_holds
        WHERE guest_id = ?
        """,
        (guest_id,)
    ).fetchone()

    reservation = connection.execute(
        """
        SELECT reservation_id FROM reservations
        WHERE booking_reference = ?
        """,
        ("EXPIRED-PAYMENT-001",)
    ).fetchone()

    payment_attempt = connection.execute(
        """
        SELECT attempt_id FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    connection.close()

    assert pending_booking["status"] == "Expired"
    assert room_hold is None
    assert reservation is None
    assert payment_attempt is None

# Test 6: Tests that a guest cannot process another guest's pending booking.
def test_guest_cannot_process_another_guests_booking(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create the booking owner's guest account.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Booking Owner", "owner@example.com", "9876543210")
    )
    owner_id = cursor.lastrowid

    # Create another guest who will attempt to process the booking.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Another Guest", "another@example.com", "9876543211")
    )
    another_guest_id = cursor.lastrowid

    # Get the test room.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin_date = (
        datetime.now() + timedelta(days=10)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=12)
    ).strftime("%Y-%m-%d")

    booking_data = {
        "base_price": 3000,
        "occupants": [],
        "nightly_rates": []
    }

    # Create a pending booking belonging to the booking owner.
    cursor = connection.execute(
        """
        INSERT INTO pending_bookings (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            total_amount, booking_data, expires_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "OWNER-BOOKING-001",
            owner_id,
            room["room_id"],
            checkin_date,
            checkout_date,
            1,
            9000,
            json.dumps(booking_data),
            (datetime.now() + timedelta(minutes=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Pending"
        )
    )

    pending_booking_id = cursor.lastrowid
    connection.commit()
    connection.close()

    # Log in as the other guest, not the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = another_guest_id
        session["guest_name"] = "Another Guest"

    # Attempt to process the booking.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Successful"}
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    # Verify that the original booking remains unchanged.
    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT status FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    payment_attempt = connection.execute(
        """
        SELECT attempt_id FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    connection.close()

    assert pending_booking["status"] == "Pending"
    assert payment_attempt is None

# Test 7: Tests that an unknown pending booking ID is rejected.
def test_unknown_pending_booking_id(client):

    # Log in as a guest.
    with client.session_transaction() as session:
        session["guest_id"] = 1
        session["guest_name"] = "Test Guest"

    # Attempt payment using a booking ID that does not exist.
    response = client.post(
        "/process-payment/9999",
        data={"payment_result": "Successful"}
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    # Verify that no payment attempt was created.
    from app import get_db_connection

    connection = get_db_connection()

    payment_attempt = connection.execute(
        """
        SELECT attempt_id
        FROM payment_attempts
        WHERE pending_booking_id = 9999
        """
    ).fetchone()

    connection.close()

    assert payment_attempt is None

# Test 8: Tests that an already-processed booking cannot be paid for again.
def test_already_processed_booking_cannot_be_paid_again(
    client, room_test_data
):
    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create a guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Processed Guest", "processed@example.com", "9876543212")
    )
    guest_id = cursor.lastrowid

    # Get the test room.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin_date = (
        datetime.now() + timedelta(days=10)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=12)
    ).strftime("%Y-%m-%d")

    booking_data = {
        "base_price": 3000,
        "occupants": [],
        "nightly_rates": []
    }

    # Create a pending booking that has already been completed.
    cursor = connection.execute(
        """
        INSERT INTO pending_bookings (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            total_amount, booking_data, expires_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "PROCESSED-BOOKING-001",
            guest_id,
            room["room_id"],
            checkin_date,
            checkout_date,
            1,
            9000,
            json.dumps(booking_data),
            (datetime.now() + timedelta(minutes=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Completed"
        )
    )

    pending_booking_id = cursor.lastrowid
    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Processed Guest"

    # Attempt to pay for the already-completed booking again.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Successful"}
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    # Verify that the booking remains completed and no new attempt exists.
    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT status FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    payment_attempts = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    reservations = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM reservations
        WHERE booking_reference = ?
        """,
        ("PROCESSED-BOOKING-001",)
    ).fetchone()

    connection.close()

    assert pending_booking["status"] == "Completed"
    assert payment_attempts["total"] == 0
    assert reservations["total"] == 0

# Test 9: Tests that guests must log in before accessing the payment page.
def test_payment_page_requires_guest_login(client):

    response = client.get(
        "/payment/1",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 10: Tests that a logged-in guest can access a valid payment page.
def test_payment_page_loads_for_valid_booking(client, room_test_data):

    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create a test guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Payment Page Guest", "paymentpage@example.com", "9876543213")
    )
    guest_id = cursor.lastrowid

    # Get the test room.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin_date = (
        datetime.now() + timedelta(days=10)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=12)
    ).strftime("%Y-%m-%d")

    booking_data = {
        "base_price": 3000,
        "occupants": [],
        "nightly_rates": []
    }

    # Create a valid pending booking with a future expiry time.
    cursor = connection.execute(
        """
        INSERT INTO pending_bookings (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            total_amount, booking_data, expires_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "PAYMENT-PAGE-001",
            guest_id,
            room["room_id"],
            checkin_date,
            checkout_date,
            1,
            9000,
            json.dumps(booking_data),
            (datetime.now() + timedelta(minutes=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Pending"
        )
    )

    pending_booking_id = cursor.lastrowid

    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Payment Page Guest"

    # Open the payment page.
    response = client.get(
        f"/payment/{pending_booking_id}"
    )

    assert response.status_code == 200
    assert b"PAYMENT-PAGE-001" in response.data
    assert b"TEST-101" in response.data

# Test 11: Tests that a guest cannot access another guest's payment page.
def test_guest_cannot_access_another_guests_payment_page(
    client, room_test_data
):
    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create the booking owner.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Payment Owner", "paymentowner@example.com", "9876543214")
    )
    owner_id = cursor.lastrowid

    # Create another guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Other Guest", "otherguest@example.com", "9876543215")
    )
    other_guest_id = cursor.lastrowid

    # Get the test room.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin_date = (
        datetime.now() + timedelta(days=10)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=12)
    ).strftime("%Y-%m-%d")

    booking_data = {
        "base_price": 3000,
        "occupants": [],
        "nightly_rates": []
    }

    # Create a valid pending booking for the owner.
    cursor = connection.execute(
        """
        INSERT INTO pending_bookings (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            total_amount, booking_data, expires_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "OWNER-PAYMENT-001",
            owner_id,
            room["room_id"],
            checkin_date,
            checkout_date,
            1,
            9000,
            json.dumps(booking_data),
            (datetime.now() + timedelta(minutes=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Pending"
        )
    )

    pending_booking_id = cursor.lastrowid

    connection.commit()
    connection.close()

    # Log in as the other guest.
    with client.session_transaction() as session:
        session["guest_id"] = other_guest_id
        session["guest_name"] = "Other Guest"

    # Attempt to access the owner's payment page.
    response = client.get(
        f"/payment/{pending_booking_id}",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"

# Test 12: Tests that an expired pending booking cannot access the payment page.
def test_expired_booking_cannot_access_payment_page(
    client, room_test_data
):
    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create a test guest.
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Expired Page Guest", "expiredpage@example.com", "9876543216")
    )
    guest_id = cursor.lastrowid

    # Get the test room.
    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin_date = (
        datetime.now() + timedelta(days=10)
    ).strftime("%Y-%m-%d")

    checkout_date = (
        datetime.now() + timedelta(days=12)
    ).strftime("%Y-%m-%d")

    booking_data = {
        "base_price": 3000,
        "occupants": [],
        "nightly_rates": []
    }

    # Create a pending booking whose payment window has expired.
    cursor = connection.execute(
        """
        INSERT INTO pending_bookings (
            booking_reference, guest_id, room_id,
            checkin_date, checkout_date, number_of_guests,
            total_amount, booking_data, expires_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "EXPIRED-PAGE-001",
            guest_id,
            room["room_id"],
            checkin_date,
            checkout_date,
            1,
            9000,
            json.dumps(booking_data),
            (datetime.now() - timedelta(minutes=5)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Pending"
        )
    )

    pending_booking_id = cursor.lastrowid

    connection.commit()
    connection.close()

    # Log in as the booking owner.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Expired Page Guest"

    # Attempt to access the expired payment page.
    response = client.get(
        f"/payment/{pending_booking_id}",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    # Verify that the expired booking was deleted.
    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT pending_booking_id
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    connection.close()

    assert pending_booking is None