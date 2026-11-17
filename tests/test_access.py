# Test 1: Checks that unauthenticated users cannot access the Administrator Dashboard.
def test_admin_dashboard_requires_login(client):

    response = client.get("/admin-dashboard")

    assert response.status_code == 302
    assert "/staff-login" in response.headers["Location"]

# Test 2: Checks that Receptionists cannot access the Administrator Dashboard.
def test_receptionist_cannot_access_admin_dashboard(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Receptionist"

    response = client.get("/admin-dashboard")

    assert response.status_code == 403

# Test 3: Checks that Housekeeping Staff cannot access the Administrator Dashboard.
def test_housekeeping_staff_cannot_access_admin_dashboard(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Housekeeping Staff"

    response = client.get("/admin-dashboard")

    assert response.status_code == 403

# Test 4: Checks that Administrators can access the Administrator Dashboard.
def test_admin_can_access_admin_dashboard(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Administrator"

    response = client.get("/admin-dashboard")

    assert response.status_code == 200

# Test 5: Checks that unauthenticated users cannot access the Receptionist Dashboard.
def test_receptionist_dashboard_requires_login(client):

    response = client.get("/receptionist-dashboard")

    assert response.status_code == 302
    assert "/staff-login" in response.headers["Location"]

# Test 6: Checks that Housekeeping Staff cannot access the Receptionist Dashboard.
def test_housekeeping_staff_cannot_access_receptionist_dashboard(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Housekeeping Staff"

    response = client.get("/receptionist-dashboard")

    assert response.status_code == 403

# Test 7: Checks that Receptionists can access the Receptionist Dashboard.
def test_receptionist_can_access_receptionist_dashboard(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Receptionist"

    response = client.get("/receptionist-dashboard")

    assert response.status_code == 200

# Test 8: Checks that Administrators can also access the Receptionist Dashboard.
def test_admin_can_access_receptionist_dashboard(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Administrator"

    response = client.get("/receptionist-dashboard")

    assert response.status_code == 200

# Test 9: Checks that unauthenticated users cannot access Guest Management.
def test_guest_management_requires_login(client):

    response = client.get("/guest-management")

    assert response.status_code == 302
    assert "/staff-login" in response.headers["Location"]

# Test 10: Checks that Housekeeping Staff cannot access Guest Management.
def test_housekeeping_staff_cannot_access_guest_management(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Housekeeping Staff"

    response = client.get("/guest-management")

    assert response.status_code == 403

# Test 11: Checks that Receptionists can access Guest Management.
def test_receptionist_can_access_guest_management(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Receptionist"

    response = client.get("/guest-management")

    assert response.status_code == 200

# Test 12: Checks that Administrators can access Guest Management.
def test_admin_can_access_guest_management(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Administrator"

    response = client.get("/guest-management")

    assert response.status_code == 200

# Test 13: Checks that unauthenticated users cannot view a guest's booking history.
def test_guest_bookings_requires_staff_login(client):

    response = client.get("/guest-bookings/1")

    assert response.status_code == 302
    assert "/staff-login" in response.headers["Location"]

# Test 14: Checks that Housekeeping Staff cannot view guest booking history.
def test_housekeeping_staff_cannot_view_guest_bookings(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Housekeeping Staff"

    response = client.get("/guest-bookings/1")

    assert response.status_code == 403

# Test 15: Checks that accessing booking history for a non-existing guest returns 404.
def test_guest_bookings_returns_404_for_invalid_guest(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = "Administrator"

    response = client.get("/guest-bookings/9999")

    assert response.status_code == 404
    assert b"Guest not found" in response.data

# Test 16: Checks that guests must log in before viewing their bookings.
def test_my_bookings_requires_guest_login(client):

    response = client.get("/my-bookings")

    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 17: Checks that guests must log in before checking room availability.
def test_check_availability_requires_guest_login(client):

    response = client.post(
        "/check-availability",
        data={}
    )

    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 18: Checks that guests must log in before accessing the reservation form.
def test_reservation_requires_guest_login(client):

    response = client.post(
        "/reservation",
        data={}
    )

    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 19: Checks that guests must log in before confirming a reservation.
def test_confirm_reservation_requires_guest_login(client):

    response = client.post(
        "/confirm-reservation",
        data={}
    )

    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 20: Checks that guests must log in before accessing the payment page.
def test_payment_page_requires_guest_login(client):

    response = client.get("/payment/1")

    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 21: Checks that unauthenticated users cannot access a pending booking QR code.
def test_pending_qr_requires_guest_login(client):

    response = client.get("/pending-qr/1")

    assert response.status_code == 401
    assert b"Unauthorized" in response.data

# Test 22: Checks that guests must log in before processing a payment.
def test_process_payment_requires_guest_login(client):

    response = client.post(
        "/process-payment/1",
        data={"payment_result": "Successful"}
    )

    assert response.status_code == 302
    assert "/guest-login" in response.headers["Location"]

# Test 23: Checks that guest logout clears the session and redirects to the homepage.
def test_guest_logout_clears_session(client):

    with client.session_transaction() as session:
        session["guest_id"] = 1
        session["guest_name"] = "Test Guest"
        session["guest_email"] = "testguest@example.com"

    response = client.get("/guest-logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    with client.session_transaction() as session:
        assert len(session) == 0

# Test 24: Checks that staff logout clears the session and redirects to staff login.
def test_staff_logout_clears_session(client):

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    response = client.get("/staff-logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/staff-login")

    with client.session_transaction() as session:
        assert len(session) == 0
