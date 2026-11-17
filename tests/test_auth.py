# Test 1: Checks whether the Flask application is running in testing mode.
def test_app_is_in_testing_mode(app):
    assert app.config["TESTING"] is True

# Test 2: Checks whether the Flask application instance is created successfully.
def test_flask_application_exists(app):
    assert app is not None

# Test 3: Checks whether a guest can register successfully using valid details.
def test_guest_registration_success(client):
    response = client.post(
        "/guest-register",
        data={
            "full_name": "Test Guest",
            "email": "testguest@example.com",
            "phone": "9876543210",
            "password": "Guest@123",
            "confirm_password": "Guest@123"
        }
    )

    assert response.status_code == 302
    assert "/guest-login" in response.location

# Test 4: Checks whether registration is rejected when any required field is missing.
def test_guest_registration_missing_fields(client):
    response = client.post(
        "/guest-register",
        data={
            "full_name": "",
            "email": "testguest@example.com",
            "phone": "9876543210",
            "password": "Guest@123",
            "confirm_password": "Guest@123"
        }
    )

    assert response.status_code == 400
    assert b"All fields are required." in response.data

# Test 5: Checks whether registration is rejected when the phone number is not 10 digits.
def test_guest_registration_invalid_phone(client):
    response = client.post(
        "/guest-register",
        data={
            "full_name": "Test Guest",
            "email": "testguest@example.com",
            "phone": "98765",
            "password": "Guest@123",
            "confirm_password": "Guest@123"
        }
    )

    assert response.status_code == 400
    assert b"valid 10-digit phone number" in response.data


# Test 6: Checks whether registration is rejected when the password has fewer than 8 characters.
def test_guest_registration_short_password(client):
    response = client.post(
        "/guest-register",
        data={
            "full_name": "Test Guest",
            "email": "testguest@example.com",
            "phone": "9876543210",
            "password": "Guest1",
            "confirm_password": "Guest1"
        }
    )

    assert response.status_code == 400
    assert b"at least 8 characters" in response.data

# Test 7: Checks whether registration is rejected when the password and confirmation do not match.
def test_guest_registration_password_mismatch(client):
    response = client.post(
        "/guest-register",
        data={
            "full_name": "Test Guest",
            "email": "testguest@example.com",
            "phone": "9876543210",
            "password": "Guest@123",
            "confirm_password": "Different@123"
        }
    )

    assert response.status_code == 400
    assert b"Passwords do not match." in response.data

# Test 8: Checks whether registration is rejected when an email address is already registered.
def test_guest_registration_duplicate_email(client):
    client.post(
        "/guest-register",
        data={
            "full_name": "First Guest",
            "email": "duplicate@example.com",
            "phone": "9876543210",
            "password": "Guest@123",
            "confirm_password": "Guest@123"
        }
    )

    response = client.post(
        "/guest-register",
        data={
            "full_name": "Second Guest",
            "email": "duplicate@example.com",
            "phone": "9876543211",
            "password": "Guest@123",
            "confirm_password": "Guest@123"
        }
    )

    assert response.status_code == 409
    assert b"already exists" in response.data