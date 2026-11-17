# Integration Test 1:

# Checks whether room availability, reservation form and pending booking creation work together.

def test_availability_to_pending_booking(
    client, room_test_data
):

    from app import get_db_connection

    # Create a guest.
    connection = get_db_connection()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Integration Guest", "integration@example.com", "9876543210")
    )

    guest_id = cursor.lastrowid

    connection.commit()
    connection.close()

    # Log in as the guest.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Integration Guest"
        session["guest_email"] = "integration@example.com"

    # Step 1: Check room availability.
    availability_response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-12-10",
            "checkout_date": "2026-12-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert availability_response.status_code == 200
    assert b"Rooms Available!" in availability_response.data

    # Step 2: Proceed to the reservation form.
    reservation_response = client.post(
        "/reservation",
        data={
            "checkin_date": "2026-12-10",
            "checkout_date": "2026-12-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"]),
            "total_amount": "6000"
        }
    )

    assert reservation_response.status_code == 200

    # Step 3: Confirm the reservation details.
    confirmation_response = client.post(
        "/confirm-reservation",
        data={
            "checkin_date": "2026-12-10",
            "checkout_date": "2026-12-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"]),
            "phone": "9876543210",
            "address": "Mapusa, Goa",
            "id_type": "Aadhaar",
            "id_number": "TEST123456",
            "occupant_name[]": [
                "Integration Guest",
                "Second Guest"
            ],
            "occupant_age[]": ["22", "24"]
        }
    )

    assert confirmation_response.status_code == 200

    # Step 4: Verify the pending booking was created.
    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT *
        FROM pending_bookings
        WHERE guest_id = ?
        """,
        (guest_id,)
    ).fetchone()

    assert pending_booking is not None
    assert pending_booking["status"] == "Pending"
    assert pending_booking["checkin_date"] == "2026-12-10"
    assert pending_booking["checkout_date"] == "2026-12-12"

    # Step 5: Verify that the room was temporarily held.
    room_hold = connection.execute(
        """
        SELECT *
        FROM room_holds
        WHERE guest_id = ?
        """,
        (guest_id,)
    ).fetchone()

    assert room_hold is not None
    assert room_hold["room_id"] == pending_booking["room_id"]

    connection.close()

# ----------------------------------------
# Helper Function: Create Pending Booking
# ----------------------------------------

def create_pending_booking(client, room_test_data, email):

    from app import get_db_connection

    # Create a guest.
    connection = get_db_connection()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Payment Integration Guest", email, "9876543210")
    )

    guest_id = cursor.lastrowid

    connection.commit()
    connection.close()

    # Log in as the guest.
    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Payment Integration Guest"
        session["guest_email"] = email

    # Check room availability.
    availability_response = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-12-10",
            "checkout_date": "2026-12-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert availability_response.status_code == 200

    # Create the pending booking.
    confirmation_response = client.post(
        "/confirm-reservation",
        data={
            "checkin_date": "2026-12-10",
            "checkout_date": "2026-12-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"]),
            "phone": "9876543210",
            "address": "Mapusa, Goa",
            "id_type": "Aadhaar",
            "id_number": "TEST123456",
            "occupant_name[]": [
                "Payment Integration Guest",
                "Second Guest"
            ],
            "occupant_age[]": ["22", "24"]
        }
    )

    assert confirmation_response.status_code == 200

    # Retrieve the pending booking.
    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT *
        FROM pending_bookings
        WHERE guest_id = ?
        """,
        (guest_id,)
    ).fetchone()

    assert pending_booking is not None
    assert pending_booking["status"] == "Pending"

    pending_booking_id = pending_booking["pending_booking_id"]

    connection.close()

    return guest_id, pending_booking_id

# ----------------------------------------
# Integration Test 2.1:
# Successful Payment
# ----------------------------------------

def test_successful_payment_confirms_reservation(
    client, room_test_data
):

    from app import get_db_connection

    # Create a pending booking.
    guest_id, pending_booking_id = create_pending_booking(
        client,
        room_test_data,
        "payment_success@example.com"
    )

    # Retrieve the pending booking details.
    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT *
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    expected_amount = pending_booking["total_amount"]
    room_id = pending_booking["room_id"]

    connection.close()

    # Process successful payment.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Successful"},
        follow_redirects=True
    )

    assert response.status_code == 200

    # Verify the reservation, payment and pending booking.
    connection = get_db_connection()

    reservation = connection.execute(
        """
        SELECT *
        FROM reservations
        WHERE booking_reference = ?
        """,
        (pending_booking["booking_reference"],)
    ).fetchone()

    assert reservation is not None
    assert reservation["booking_status"] == "Confirmed"
    assert reservation["payment_status"] == "Successful"
    assert reservation["total_amount"] == expected_amount
    assert reservation["room_id"] == room_id

    # Verify the successful payment record.
    payment = connection.execute(
        """
        SELECT *
        FROM payments
        WHERE reservation_id = ?
        """,
        (reservation["reservation_id"],)
    ).fetchone()

    assert payment is not None
    assert payment["payment_status"] == "Successful"
    assert payment["payment_amount"] == expected_amount

    # Verify the payment attempt.
    payment_attempt = connection.execute(
        """
        SELECT *
        FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert payment_attempt is not None
    assert payment_attempt["payment_status"] == "Successful"

    # Verify occupant details were transferred.
    occupants = connection.execute(
        """
        SELECT *
        FROM reservation_occupants
        WHERE reservation_id = ?
        """,
        (reservation["reservation_id"],)
    ).fetchall()

    assert len(occupants) == 2

    # Verify nightly pricing records were transferred.
    nightly_rates = connection.execute(
        """
        SELECT *
        FROM reservation_nightly_rates
        WHERE reservation_id = ?
        """,
        (reservation["reservation_id"],)
    ).fetchall()

    assert len(nightly_rates) == 2

    # Verify pending booking is completed.
    updated_booking = connection.execute(
        """
        SELECT status
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert updated_booking["status"] == "Completed"

    # Verify room hold was released.
    room_hold = connection.execute(
        """
        SELECT *
        FROM room_holds
        WHERE room_id = ?
          AND guest_id = ?
        """,
        (room_id, guest_id)
    ).fetchone()

    assert room_hold is None

    connection.close()

# ----------------------------------------
# Integration Test 2.2:
# Failed Payment
# ----------------------------------------

def test_failed_payment_releases_room(
    client, room_test_data
):

    from app import get_db_connection

    # Create a pending booking.
    guest_id, pending_booking_id = create_pending_booking(
        client,
        room_test_data,
        "payment_failed@example.com"
    )

    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT room_id
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    room_id = pending_booking["room_id"]

    connection.close()

    # Process failed payment.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Failed"}
    )

    assert response.status_code == 200

    connection = get_db_connection()

    # Verify pending booking status.
    booking = connection.execute(
        """
        SELECT status
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert booking["status"] == "Failed"

    # Verify failed payment attempt.
    payment_attempt = connection.execute(
        """
        SELECT payment_status
        FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert payment_attempt is not None
    assert payment_attempt["payment_status"] == "Failed"

    # Verify no confirmed reservation was created.
    reservation = connection.execute(
        """
        SELECT reservation_id
        FROM reservations
        WHERE booking_reference = (
            SELECT booking_reference
            FROM pending_bookings
            WHERE pending_booking_id = ?
        )
        """,
        (pending_booking_id,)
    ).fetchone()

    assert reservation is None

    # Verify room hold was released.
    room_hold = connection.execute(
        """
        SELECT *
        FROM room_holds
        WHERE room_id = ?
          AND guest_id = ?
        """,
        (room_id, guest_id)
    ).fetchone()

    assert room_hold is None

    connection.close()

# ----------------------------------------
# Integration Test 2.3:
# Invalid Payment Selection
# ----------------------------------------

def test_invalid_payment_selection(
    client, room_test_data
):

    from app import get_db_connection

    # Create a pending booking.
    guest_id, pending_booking_id = create_pending_booking(
        client,
        room_test_data,
        "payment_invalid@example.com"
    )

    # Submit an invalid payment result.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Invalid"}
    )

    assert response.status_code == 302

    connection = get_db_connection()

    # Verify pending booking remains unchanged.
    booking = connection.execute(
        """
        SELECT status
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert booking["status"] == "Pending"

    # Verify no payment attempt was created.
    payment_attempt = connection.execute(
        """
        SELECT *
        FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert payment_attempt is None

    # Verify room hold still exists.
    room_hold = connection.execute(
        """
        SELECT *
        FROM room_holds
        WHERE guest_id = ?
        """,
        (guest_id,)
    ).fetchone()

    assert room_hold is not None

    connection.close()

# ----------------------------------------
# Integration Test 2.4:
# Unauthorized Payment Access
# ----------------------------------------

def test_guest_cannot_process_another_guests_payment(
    client, room_test_data
):

    from app import get_db_connection

    # Create the original guest's pending booking.
    guest_id, pending_booking_id = create_pending_booking(
        client,
        room_test_data,
        "payment_owner@example.com"
    )

    # Create another guest.
    connection = get_db_connection()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Unauthorized Guest", "unauthorized@example.com", "9876543211")
    )

    other_guest_id = cursor.lastrowid

    connection.commit()
    connection.close()

    # Log in as the other guest.
    with client.session_transaction() as session:
        session["guest_id"] = other_guest_id
        session["guest_name"] = "Unauthorized Guest"
        session["guest_email"] = "unauthorized@example.com"

    # Attempt to process the original guest's payment.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Successful"}
    )

    assert response.status_code == 302
    assert response.location == "/"

    connection = get_db_connection()

    # Verify original booking remains pending.
    booking = connection.execute(
        """
        SELECT status
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert booking["status"] == "Pending"

    # Verify no payment attempt was created.
    payment_attempt = connection.execute(
        """
        SELECT *
        FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert payment_attempt is None

    # Verify original guest's room hold remains.
    room_hold = connection.execute(
        """
        SELECT *
        FROM room_holds
        WHERE guest_id = ?
        """,
        (guest_id,)
    ).fetchone()

    assert room_hold is not None

    connection.close()

# ----------------------------------------
# Integration Test 2.5:
# Expired Pending Booking
# ----------------------------------------

def test_expired_pending_booking_cannot_be_paid(
    client, room_test_data
):

    from app import get_db_connection
    from datetime import datetime, timedelta

    # Create a pending booking.
    guest_id, pending_booking_id = create_pending_booking(
        client,
        room_test_data,
        "payment_expired@example.com"
    )

    connection = get_db_connection()

    pending_booking = connection.execute(
        """
        SELECT room_id
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    room_id = pending_booking["room_id"]

    # Set payment expiry time in the past.
    expired_time = (
        datetime.now() - timedelta(minutes=5)
    ).strftime("%Y-%m-%d %H:%M:%S")

    connection.execute(
        """
        UPDATE pending_bookings
        SET expires_at = ?
        WHERE pending_booking_id = ?
        """,
        (expired_time, pending_booking_id)
    )

    connection.commit()
    connection.close()

    # Attempt successful payment after expiry.
    response = client.post(
        f"/process-payment/{pending_booking_id}",
        data={"payment_result": "Successful"}
    )

    assert response.status_code == 302

    connection = get_db_connection()

    # Verify booking is marked as expired.
    booking = connection.execute(
        """
        SELECT status
        FROM pending_bookings
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert booking["status"] == "Expired"

    # Verify no payment attempt was created.
    payment_attempt = connection.execute(
        """
        SELECT *
        FROM payment_attempts
        WHERE pending_booking_id = ?
        """,
        (pending_booking_id,)
    ).fetchone()

    assert payment_attempt is None

    # Verify room hold was released.
    room_hold = connection.execute(
        """
        SELECT *
        FROM room_holds
        WHERE room_id = ?
          AND guest_id = ?
        """,
        (room_id, guest_id)
    ).fetchone()

    assert room_hold is None

    connection.close()

# ----------------------------------------
# Integration Test 3:
# Reservation → Billing PDF
# ----------------------------------------

def test_reservation_generates_billing_pdf(
    client, room_test_data
):

    from app import get_db_connection
    from io import BytesIO
    from pypdf import PdfReader

    # Step 1: Create a pending reservation.
    guest_id, pending_booking_id = create_pending_booking(
        client,
        room_test_data,
        "billing_integration@example.com"
    )

    # Step 2: Retrieve booking details.
    connection = get_db_connection()

    booking = connection.execute(
        """
        SELECT
            pb.booking_reference,
            pb.checkin_date,
            pb.checkout_date,
            pb.total_amount,
            pb.number_of_guests,
            rm.room_number,
            rc.category_name
        FROM pending_bookings pb
        JOIN rooms rm ON pb.room_id = rm.room_id
        JOIN room_categories rc
            ON rm.category_id = rc.category_id
        WHERE pb.pending_booking_id = ?
          AND pb.guest_id = ?
        """,
        (pending_booking_id, guest_id)
    ).fetchone()

    assert booking is not None

    booking_reference = booking["booking_reference"]
    room_number = str(booking["room_number"])

    connection.close()

    # Step 3: Generate the billing PDF.
    response = client.get(
        f"/generate-bill/{pending_booking_id}"
    )

    # Verify successful PDF response.
    assert response.status_code == 200
    assert response.content_type == "application/pdf"
    assert response.data.startswith(b"%PDF")

    # Step 4: Extract text from the generated PDF.
    pdf_reader = PdfReader(BytesIO(response.data))

    pdf_text = ""

    for page in pdf_reader.pages:
        pdf_text += page.extract_text() or ""

    # Step 5: Verify booking information in the PDF.
    assert booking_reference in pdf_text
    assert "Payment Integration Guest" in pdf_text
    assert "billing_integration@example.com" in pdf_text
    assert room_number in pdf_text
    assert booking["category_name"] in pdf_text

    # Verify reservation dates.
    assert "2026-12-10" in pdf_text
    assert "2026-12-12" in pdf_text

    # Verify occupant details.
    assert "Second Guest" in pdf_text

    # Verify total amount.
    assert str(int(booking["total_amount"])) in pdf_text

# ----------------------------------------
# Integration Test 4:
# Guest Registration → Login
# ----------------------------------------

def test_guest_registration_to_login(client):

    from app import get_db_connection
    import bcrypt

    # Step 1: Register a new guest.
    registration_response = client.post(
        "/guest-register",
        data={
            "full_name": "Registration Integration Guest",
            "email": "registration_integration@example.com",
            "phone": "9876543210",
            "password": "TestPass123",
            "confirm_password": "TestPass123"
        }
    )

    # Verify registration redirects to login.
    assert registration_response.status_code == 302
    assert "/guest-login" in registration_response.location

    # Step 2: Verify guest details are saved.
    connection = get_db_connection()

    guest = connection.execute(
        """
        SELECT *
        FROM guests
        WHERE email = ?
        """,
        ("registration_integration@example.com",)
    ).fetchone()

    assert guest is not None
    assert guest["full_name"] == "Registration Integration Guest"
    assert guest["phone"] == "9876543210"

    # Verify password is hashed.
    assert guest["password_hash"] != "TestPass123"

    assert bcrypt.checkpw(
        "TestPass123".encode("utf-8"),
        guest["password_hash"].encode("utf-8")
    )

    guest_id = guest["guest_id"]

    connection.close()

    # Step 3: Log in using the registered credentials.
    login_response = client.post(
        "/guest-login",
        data={
            "email": "registration_integration@example.com",
            "password": "TestPass123"
        }
    )

    # Verify successful login redirects to home.
    assert login_response.status_code == 302
    assert login_response.location == "/"

    # Step 4: Verify guest session.
    with client.session_transaction() as session:

        assert session["guest_id"] == guest_id
        assert session["guest_name"] == "Registration Integration Guest"
        assert session["guest_email"] == "registration_integration@example.com"

# ----------------------------------------
# Integration Test 5:
# Housekeeping → Room Availability
# ----------------------------------------

def test_housekeeping_updates_room_availability(
    client, room_test_data
):

    from app import get_db_connection

    # Step 1: Retrieve the test room.
    connection = get_db_connection()

    room = connection.execute(
        """
        SELECT room_id
        FROM rooms
        WHERE room_number = ?
        """,
        (room_test_data["room_number"],)
    ).fetchone()

    assert room is not None

    room_id = room["room_id"]

    # Set the room initially as Dirty/Vacant.
    connection.execute(
        """
        UPDATE rooms
        SET housekeeping_status = 'Dirty/Vacant'
        WHERE room_id = ?
        """,
        (room_id,)
    )

    # Create a Housekeeping Staff user.
    cursor = connection.execute(
        """
        INSERT INTO users (
            full_name,
            email,
            password_hash,
            role
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            "Integration Housekeeper",
            "integration_housekeeper@example.com",
            "test_password_hash",
            "Housekeeping Staff"
        )
    )

    user_id = cursor.lastrowid

    # Create a guest for the availability search.
    guest_cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        (
            "Availability Integration Guest",
            "availability_integration@example.com",
            "9876543210"
        )
    )

    guest_id = guest_cursor.lastrowid

    connection.commit()
    connection.close()

    # Step 2: Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Integration Housekeeper"
        session["role"] = "Housekeeping Staff"
        session["guest_id"] = guest_id
        session["guest_name"] = "Availability Integration Guest"
        session["guest_email"] = "availability_integration@example.com"

    # Step 3: Start room cleaning.
    start_response = client.post(
        f"/start-cleaning/{room_id}"
    )

    assert start_response.status_code == 302

    # Verify room is now being cleaned.
    connection = get_db_connection()

    updated_room = connection.execute(
        """
        SELECT housekeeping_status
        FROM rooms
        WHERE room_id = ?
        """,
        (room_id,)
    ).fetchone()

    assert updated_room["housekeeping_status"] == "Cleaning In Progress"

    # Verify housekeeping assignment was created.
    assignment = connection.execute(
        """
        SELECT *
        FROM housekeeping_assignments
        WHERE room_id = ?
          AND assigned_to = ?
        """,
        (room_id, user_id)
    ).fetchone()

    assert assignment is not None
    assert assignment["cleaning_status"] == "Cleaning In Progress"

    connection.close()

    # Step 4: Check availability while cleaning.
    cleaning_availability = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert cleaning_availability.status_code == 200

    # Room should not appear while cleaning.
    assert room_test_data["room_number"].encode() not in cleaning_availability.data

    # Step 5: Complete room cleaning.
    complete_response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    assert complete_response.status_code == 302

    # Verify room is now Clean/Ready.
    connection = get_db_connection()

    updated_room = connection.execute(
        """
        SELECT housekeeping_status
        FROM rooms
        WHERE room_id = ?
        """,
        (room_id,)
    ).fetchone()

    assert updated_room["housekeeping_status"] == "Clean/Ready"

    # Verify housekeeping assignment is completed.
    completed_assignment = connection.execute(
        """
        SELECT cleaning_status
        FROM housekeeping_assignments
        WHERE room_id = ?
          AND assigned_to = ?
        ORDER BY assignment_id DESC
        LIMIT 1
        """,
        (room_id, user_id)
    ).fetchone()

    assert completed_assignment["cleaning_status"] == "Completed"

    connection.close()

    # Step 6: Check availability after cleaning.
    ready_availability = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert ready_availability.status_code == 200

    # Availability page should display the available rooms message.
    assert b"Rooms Available!" in ready_availability.data

# ----------------------------------------
# Integration Test 6:
# Maintenance → Room Availability
# ----------------------------------------

def test_maintenance_updates_room_availability(
    client, room_test_data
):

    from app import get_db_connection

    # Step 1: Retrieve the test room.
    connection = get_db_connection()

    room = connection.execute(
        """
        SELECT room_id
        FROM rooms
        WHERE room_number = ?
        """,
        (room_test_data["room_number"],)
    ).fetchone()

    assert room is not None

    room_id = room["room_id"]

    # Create Housekeeping Staff user.
    cursor = connection.execute(
        """
        INSERT INTO users (
            full_name, email, password_hash, role
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            "Maintenance Housekeeper",
            "maintenance_housekeeper@example.com",
            "test_password_hash",
            "Housekeeping Staff"
        )
    )

    housekeeping_user_id = cursor.lastrowid

    # Create Administrator user.
    cursor = connection.execute(
        """
        INSERT INTO users (
            full_name, email, password_hash, role
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            "Maintenance Admin",
            "maintenance_admin@example.com",
            "test_password_hash",
            "Administrator"
        )
    )

    admin_user_id = cursor.lastrowid

    # Create guest for availability search.
    guest_cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        (
            "Maintenance Integration Guest",
            "maintenance_guest@example.com",
            "9876543210"
        )
    )

    guest_id = guest_cursor.lastrowid

    connection.commit()
    connection.close()

    # Step 2: Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Maintenance Housekeeper"
        session["role"] = "Housekeeping Staff"
        session["guest_id"] = guest_id

    # Step 3: Report a maintenance issue.
    report_response = client.post(
        "/report-maintenance",
        data={
            "room_id": str(room_id),
            "issue_description": "Air conditioner not working"
        }
    )

    assert report_response.status_code == 302

    # Verify maintenance report was created.
    connection = get_db_connection()

    report = connection.execute(
        """
        SELECT report_id, maintenance_status
        FROM maintenance_reports
        WHERE room_id = ?
          AND reported_by = ?
        ORDER BY report_id DESC
        LIMIT 1
        """,
        (room_id, housekeeping_user_id)
    ).fetchone()

    assert report is not None
    assert report["maintenance_status"] == "Reported"

    report_id = report["report_id"]

    # Verify room is under maintenance.
    updated_room = connection.execute(
        """
        SELECT maintenance_status
        FROM rooms
        WHERE room_id = ?
        """,
        (room_id,)
    ).fetchone()

    assert updated_room["maintenance_status"] == "Under Maintenance"

    connection.close()

    # Step 4: Check availability during maintenance.
    maintenance_availability = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert maintenance_availability.status_code == 200

    # Room should not be available during maintenance.
    assert b"No Rooms Available" in maintenance_availability.data

    # Step 5: Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = admin_user_id
        session["full_name"] = "Maintenance Admin"
        session["role"] = "Administrator"
        session["guest_id"] = guest_id

    # Move maintenance report from Reported to In Progress.
    progress_response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={
            "maintenance_status": "In Progress"
        }
    )

    assert progress_response.status_code == 302

    # Step 6: Resolve the maintenance report.
    resolve_response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={
            "maintenance_status": "Resolved"
        }
    )

    assert resolve_response.status_code == 302

    # Verify report is resolved.
    connection = get_db_connection()

    resolved_report = connection.execute(
        """
        SELECT maintenance_status
        FROM maintenance_reports
        WHERE report_id = ?
        """,
        (report_id,)
    ).fetchone()

    assert resolved_report["maintenance_status"] == "Resolved"

    # Verify room is operational again.
    updated_room = connection.execute(
        """
        SELECT maintenance_status
        FROM rooms
        WHERE room_id = ?
        """,
        (room_id,)
    ).fetchone()

    assert updated_room["maintenance_status"] == "Operational"

    connection.close()

    # Step 7: Check availability after maintenance.
    ready_availability = client.post(
        "/check-availability",
        data={
            "checkin_date": "2026-11-10",
            "checkout_date": "2026-11-12",
            "guests": "2",
            "category_id": str(room_test_data["category_id"])
        }
    )

    assert ready_availability.status_code == 200

    # Room should become available again.
    assert b"Rooms Available!" in ready_availability.data

# ----------------------------------------
# Integration Test 7:
# Staff Login → Role-Based Access
# ----------------------------------------

def test_staff_login_and_role_based_access(client):

    from app import get_db_connection
    import bcrypt

    # Step 1: Create three staff accounts.
    connection = get_db_connection()

    password = "TestPassword123"
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    staff_members = [
        (
            "Integration Admin",
            "integration_admin@example.com",
            "Administrator"
        ),
        (
            "Integration Receptionist",
            "integration_receptionist@example.com",
            "Receptionist"
        ),
        (
            "Integration Housekeeper",
            "integration_housekeeper_role@example.com",
            "Housekeeping Staff"
        )
    ]

    for full_name, email, role in staff_members:

        connection.execute(
            """
            INSERT INTO users (
                full_name,
                email,
                password_hash,
                role
            )
            VALUES (?, ?, ?, ?)
            """,
            (full_name, email, password_hash, role)
        )

    connection.commit()
    connection.close()

    # Step 2: Administrator login.
    admin_response = client.post(
        "/staff-login",
        data={
            "email": "integration_admin@example.com",
            "password": password
        }
    )

    assert admin_response.status_code == 302
    assert admin_response.headers["Location"].endswith(
        "/admin-dashboard"
    )

    with client.session_transaction() as session:
        assert session["role"] == "Administrator"

    # Administrator can access all permitted dashboards.
    assert client.get("/admin-dashboard").status_code == 200
    assert client.get("/receptionist-dashboard").status_code == 200
    assert client.get("/housekeeping-dashboard").status_code == 200

    # Step 3: Receptionist login.
    receptionist_response = client.post(
        "/staff-login",
        data={
            "email": "integration_receptionist@example.com",
            "password": password
        }
    )

    assert receptionist_response.status_code == 302
    assert receptionist_response.headers["Location"].endswith(
        "/receptionist-dashboard"
    )

    with client.session_transaction() as session:
        assert session["role"] == "Receptionist"

    # Receptionist cannot access Administrator dashboard.
    assert client.get("/admin-dashboard").status_code == 403

    # Receptionist can access permitted dashboards.
    assert client.get("/receptionist-dashboard").status_code == 200
    assert client.get("/housekeeping-dashboard").status_code == 200

    # Step 4: Housekeeping Staff login.
    housekeeping_response = client.post(
        "/staff-login",
        data={
            "email": "integration_housekeeper_role@example.com",
            "password": password
        }
    )

    assert housekeeping_response.status_code == 302
    assert housekeeping_response.headers["Location"].endswith(
        "/housekeeping-dashboard"
    )

    with client.session_transaction() as session:
        assert session["role"] == "Housekeeping Staff"

    # Housekeeping Staff cannot access restricted dashboards.
    assert client.get("/admin-dashboard").status_code == 403
    assert client.get("/receptionist-dashboard").status_code == 403

    # Housekeeping Staff can access their own dashboard.
    assert client.get("/housekeeping-dashboard").status_code == 200

# ----------------------------------------
# Integration Test 8:
# Logout → Session Cleared
# ----------------------------------------

def test_staff_logout_clears_session(client):

    # Test logout for all three staff roles.
    staff_roles = [
        "Administrator",
        "Receptionist",
        "Housekeeping Staff"
    ]

    for role in staff_roles:

        # Step 1: Create a staff login session.
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["full_name"] = "Integration Staff"
            session["role"] = role
            session["guest_id"] = 10

        # Step 2: Perform staff logout.
        response = client.get("/staff-logout")

        # Step 3: Verify redirection to staff login.
        assert response.status_code == 302
        assert response.headers["Location"].endswith(
            "/staff-login"
        )

        # Step 4: Verify that the session is completely cleared.
        with client.session_transaction() as session:
            assert len(session) == 0

        # Step 5: Verify that the logged-out user
        # cannot access the Administrator dashboard.
        dashboard_response = client.get("/admin-dashboard")

        assert dashboard_response.status_code == 302
        assert dashboard_response.headers["Location"].endswith(
            "/staff-login"
        )
