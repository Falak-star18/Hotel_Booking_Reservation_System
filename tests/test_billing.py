# Test 1: Tests that guests must log in before accessing their booking bill PDF.
def test_generate_bill_requires_guest_login(client):
    response = client.get(
        "/generate-bill/1",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 2: Tests that a logged-in guest can successfully generate a booking bill PDF.
def test_generate_bill_returns_pdf(client, room_test_data):
    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Billing Test Guest", "billingtest@example.com", "9876543217")
    )
    guest_id = cursor.lastrowid

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d")

    booking_data = {
        "guest_phone": "9876543217",
        "occupants": [
            {"occupant_name": "Billing Test Guest", "age": 22}
        ],
        "base_price": 3000,
        "nightly_rates": [
            {"stay_date": checkin, "nightly_price": 4500},
            {
                "stay_date": checkout,
                "nightly_price": 4500
            }
        ]
    }

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
            "BILL-TEST-001",
            guest_id,
            room["room_id"],
            checkin,
            checkout,
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

    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Billing Test Guest"

    response = client.get(
        f"/generate-bill/{pending_booking_id}"
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")

# Test 3: Tests that the generated PDF contains the correct booking and guest details.
def test_bill_contains_correct_booking_details(client, room_test_data):
    from app import get_db_connection
    from datetime import datetime, timedelta
    import json
    from pypdf import PdfReader
    from io import BytesIO

    connection = get_db_connection()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("PDF Detail Guest", "pdfdetails@example.com", "9876543218")
    )
    guest_id = cursor.lastrowid

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d")

    booking_data = {
        "guest_phone": "9876543218",
        "occupants": [
            {"occupant_name": "PDF Detail Guest", "age": 22}
        ],
        "base_price": 3000,
        "nightly_rates": [
            {"stay_date": checkin, "nightly_price": 4500},
            {"stay_date": checkout, "nightly_price": 4500}
        ]
    }

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
            "BILL-DETAIL-001",
            guest_id,
            room["room_id"],
            checkin,
            checkout,
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

    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "PDF Detail Guest"

    response = client.get(
        f"/generate-bill/{pending_booking_id}"
    )

    assert response.status_code == 200

    pdf_reader = PdfReader(BytesIO(response.data))
    pdf_text = "\n".join(
        page.extract_text() or "" for page in pdf_reader.pages
    )

    assert "BILL-DETAIL-001" in pdf_text
    assert "PDF Detail Guest" in pdf_text
    assert room_test_data["room_number"] in pdf_text
    assert "9000.00" in pdf_text

# Test 4: Tests that the PDF bill displays the nightly rate breakdown and correct total amount.
def test_bill_contains_nightly_rate_breakdown(client, room_test_data):
    from pypdf import PdfReader
    from app import get_db_connection
    from datetime import datetime, timedelta
    import json
    from io import BytesIO

    connection = get_db_connection()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Rate Test Guest", "ratetest@example.com", "9876543218")
    )
    guest_id = cursor.lastrowid

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d")

    booking_data = {
        "guest_phone": "9876543218",
        "occupants": [
            {"occupant_name": "Rate Test Guest", "age": 25}
        ],
        "base_price": 3000,
        "nightly_rates": [
            {"stay_date": checkin, "nightly_price": 4500},
            {
                "stay_date": (
                    datetime.now() + timedelta(days=11)
                ).strftime("%Y-%m-%d"),
                "nightly_price": 4500
            }
        ]
    }

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
            "BILL-RATE-001",
            guest_id,
            room["room_id"],
            checkin,
            checkout,
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

    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Rate Test Guest"

    response = client.get(
        f"/generate-bill/{pending_booking_id}"
    )

    assert response.status_code == 200

    pdf = PdfReader(BytesIO(response.data))
    pdf_text = "".join(
        page.extract_text() or "" for page in pdf.pages
    )

    assert checkin in pdf_text
    assert "4500.00" in pdf_text
    assert "9000.00" in pdf_text

# Test 5: Tests that the PDF bill contains the refund and tax statements.
def test_bill_contains_refund_and_tax_statements(client, room_test_data):
    from pypdf import PdfReader
    from app import get_db_connection
    from datetime import datetime, timedelta
    import json
    from io import BytesIO

    connection = get_db_connection()

    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Refund Tax Guest", "refundtax@example.com", "9876543219")
    )
    guest_id = cursor.lastrowid

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d")

    booking_data = {
        "guest_phone": "9876543219",
        "occupants": [
            {"occupant_name": "Refund Tax Guest", "age": 24}
        ],
        "base_price": 3000,
        "nightly_rates": [
            {"stay_date": checkin, "nightly_price": 4500},
            {
                "stay_date": (
                    datetime.now() + timedelta(days=11)
                ).strftime("%Y-%m-%d"),
                "nightly_price": 4500
            }
        ]
    }

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
            "BILL-TAX-001",
            guest_id,
            room["room_id"],
            checkin,
            checkout,
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

    with client.session_transaction() as session:
        session["guest_id"] = guest_id
        session["guest_name"] = "Refund Tax Guest"

    response = client.get(
        f"/generate-bill/{pending_booking_id}"
    )

    assert response.status_code == 200

    pdf = PdfReader(BytesIO(response.data))
    pdf_text = "\n".join(
        page.extract_text() or "" for page in pdf.pages
    )

    assert "Refunds are simulated and recorded by the hotel system." in pdf_text
    assert "Taxes as applicable will be EXTRA." in pdf_text

# Test 6: Tests that a guest cannot access another guest's booking bill.
def test_guest_cannot_access_another_guests_bill(client, room_test_data):
    from app import get_db_connection
    from datetime import datetime, timedelta
    import json

    connection = get_db_connection()

    # Create Guest A
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Guest A", "guesta@example.com", "9876543220")
    )
    guest_a_id = cursor.lastrowid

    # Create Guest B
    cursor = connection.execute(
        """
        INSERT INTO guests (full_name, email, phone)
        VALUES (?, ?, ?)
        """,
        ("Guest B", "guestb@example.com", "9876543221")
    )
    guest_b_id = cursor.lastrowid

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    checkin = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d")

    booking_data = {
        "guest_phone": "9876543221",
        "occupants": [
            {"occupant_name": "Guest B", "age": 25}
        ],
        "base_price": 3000,
        "nightly_rates": [
            {"stay_date": checkin, "nightly_price": 4500},
            {
                "stay_date": (
                    datetime.now() + timedelta(days=11)
                ).strftime("%Y-%m-%d"),
                "nightly_price": 4500
            }
        ]
    }

    # Create a booking belonging to Guest B
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
            "BILL-SECURITY-001",
            guest_b_id,
            room["room_id"],
            checkin,
            checkout,
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

    # Log in as Guest A
    with client.session_transaction() as session:
        session["guest_id"] = guest_a_id
        session["guest_name"] = "Guest A"

    # Guest A attempts to access Guest B's bill
    response = client.get(
        f"/generate-bill/{pending_booking_id}"
    )

    # Access must be denied
    assert response.status_code == 404
    assert b"Booking not found or access denied." in response.data

