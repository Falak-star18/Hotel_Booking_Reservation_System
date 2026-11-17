# Test 1: Tests that unauthenticated users cannot report a maintenance issue.
def test_unauthenticated_user_cannot_report_maintenance(client, room_test_data):

    # Try to report maintenance without logging in.
    response = client.post(
        "/report-maintenance",
        data={
            "room_id": 1,
            "issue_description": "Air conditioner is not working."
        },
        follow_redirects=False
    )

    # User should be redirected to staff login.
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/staff-login")

# Test 2: Tests that users other than Housekeeping Staff cannot report maintenance issues.
def test_receptionist_cannot_report_maintenance(client):

    # Log in as a Receptionist.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Receptionist"
        session["role"] = "Receptionist"

    # Try to report a maintenance issue.
    response = client.post(
        "/report-maintenance",
        data={
            "room_id": 1,
            "issue_description": "Air conditioner is not working."
        }
    )

    # Access should be denied.
    assert response.status_code == 403

# Test 3: Tests that a maintenance report cannot be submitted without selecting a room.
def test_report_maintenance_without_room(client):

    # Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Housekeeper"
        session["role"] = "Housekeeping Staff"

    # Submit a report without a room ID.
    response = client.post(
        "/report-maintenance",
        data={
            "room_id": "",
            "issue_description": "Air conditioner is not working."
        }
    )

    # The request should be rejected.
    assert response.status_code == 400
    assert b"Please select a room" in response.data

# Test 4: Tests that a maintenance report cannot be submitted without an issue description.
def test_report_maintenance_without_description(client):

    # Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Housekeeper"
        session["role"] = "Housekeeping Staff"

    # Submit a report without an issue description.
    response = client.post(
        "/report-maintenance",
        data={
            "room_id": 1,
            "issue_description": ""
        }
    )

    # The request should be rejected.
    assert response.status_code == 400
    assert b"Please select a room" in response.data

# Test 5: Tests that a maintenance report cannot be created for an invalid room.
def test_report_maintenance_for_invalid_room(client):

    # Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Housekeeper"
        session["role"] = "Housekeeping Staff"

    # Try to report an issue for a room that does not exist.
    response = client.post(
        "/report-maintenance",
        data={
            "room_id": 9999,
            "issue_description": "Air conditioner is not working."
        }
    )

    # The request should be rejected.
    assert response.status_code == 400
    assert b"Invalid room selected" in response.data

# Test 6: Tests that a second maintenance report cannot be submitted for a room already under maintenance.
def test_cannot_report_room_already_under_maintenance(client, room_test_data):

    from app import get_db_connection

    # Change the room's maintenance status to Under Maintenance.
    connection = get_db_connection()
    connection.execute("""
        UPDATE rooms
        SET maintenance_status = 'Under Maintenance'
        WHERE room_number = ?
    """, (room_test_data["room_number"],))
    connection.commit()
    connection.close()

    # Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Housekeeper"
        session["role"] = "Housekeeping Staff"

    # Try to report another issue for the same room.
    response = client.post(
        "/report-maintenance",
        data={
            "room_id": 1,
            "issue_description": "The bathroom tap is leaking."
        }
    )

    # The request should return a conflict response.
    assert response.status_code == 409
    assert b"already under maintenance" in response.data

# Test 7: Tests that Housekeeping Staff can successfully report a maintenance issue.
def test_housekeeping_staff_can_report_maintenance(client, room_test_data):

    from app import get_db_connection

    # Create a Housekeeping Staff user in the database.
    connection = get_db_connection()
    cursor = connection.execute("""
        INSERT INTO users (full_name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    """, (
        "Test Housekeeping Staff",
        "maintenance_housekeeper@example.com",
        "test_password_hash",
        "Housekeeping Staff"
    ))
    user_id = cursor.lastrowid

    # Get the test room ID.
    room = connection.execute("""
        SELECT room_id FROM rooms
        WHERE room_number = ?
    """, (room_test_data["room_number"],)).fetchone()

    room_id = room["room_id"]
    connection.commit()
    connection.close()

    # Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Housekeeping Staff"
        session["role"] = "Housekeeping Staff"

    # Submit a maintenance report.
    response = client.post(
        "/report-maintenance",
        data={
            "room_id": room_id,
            "issue_description": "Air conditioner is not working."
        },
        follow_redirects=False
    )

    # The request should redirect to the housekeeping dashboard.
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/housekeeping-dashboard")

    # Verify that the maintenance report was saved.
    connection = get_db_connection()
    report = connection.execute("""
        SELECT * FROM maintenance_reports
        WHERE room_id = ?
    """, (room_id,)).fetchone()

    # Verify that the room is marked Under Maintenance.
    room = connection.execute("""
        SELECT maintenance_status FROM rooms
        WHERE room_id = ?
    """, (room_id,)).fetchone()

    connection.close()

    assert report is not None
    assert report["issue_description"] == "Air conditioner is not working."
    assert report["maintenance_status"] == "Reported"
    assert room["maintenance_status"] == "Under Maintenance"

# Test 8: Tests that unauthenticated users cannot access the maintenance dashboard.
def test_unauthenticated_user_cannot_access_maintenance_dashboard(client):

    # Try to access the maintenance dashboard without logging in.
    response = client.get(
        "/maintenance-dashboard",
        follow_redirects=False
    )

    # The user should be redirected to staff login.
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/staff-login")

# Test 9: Tests that Housekeeping Staff cannot access the maintenance dashboard.
def test_housekeeping_staff_cannot_access_maintenance_dashboard(client):

    # Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Housekeeper"
        session["role"] = "Housekeeping Staff"

    # Try to access the maintenance dashboard.
    response = client.get("/maintenance-dashboard")

    # Access should be denied.
    assert response.status_code == 403

# Test 10: Tests that an Administrator can access the maintenance dashboard.
def test_admin_can_access_maintenance_dashboard(client):

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Access the maintenance dashboard.
    response = client.get("/maintenance-dashboard")

    # The dashboard should load successfully.
    assert response.status_code == 200
    assert b"maintenance" in response.data.lower()

# Helper function: Creates a test user and maintenance report.
def create_test_maintenance_report(room_test_data, report_status="Reported"):

    from app import get_db_connection

    connection = get_db_connection()

    # Create a test staff user.
    cursor = connection.execute("""
        INSERT INTO users (full_name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    """, (
        "Test Maintenance Staff",
        "test_maintenance_staff@example.com",
        "test_password_hash",
        "Housekeeping Staff"
    ))

    user_id = cursor.lastrowid

    # Retrieve the test room ID.
    room = connection.execute("""
        SELECT room_id FROM rooms
        WHERE room_number = ?
    """, (room_test_data["room_number"],)).fetchone()

    room_id = room["room_id"]

    # Create a maintenance report.
    cursor = connection.execute("""
        INSERT INTO maintenance_reports (
            room_id, reported_by, issue_description,
            reported_at, maintenance_status
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
    """, (
        room_id,
        user_id,
        "Test maintenance issue.",
        report_status
    ))

    report_id = cursor.lastrowid

    # Mark the room as Under Maintenance.
    connection.execute("""
        UPDATE rooms
        SET maintenance_status = 'Under Maintenance'
        WHERE room_id = ?
    """, (room_id,))

    connection.commit()
    connection.close()

    return user_id, report_id, room_id

# Test 11: Tests that a Receptionist can access the maintenance dashboard.
def test_receptionist_can_access_maintenance_dashboard(client):

    # Log in as Receptionist.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Receptionist"
        session["role"] = "Receptionist"

    # Access the maintenance dashboard.
    response = client.get("/maintenance-dashboard")

    # The dashboard should load successfully.
    assert response.status_code == 200
    assert b"maintenance" in response.data.lower()

# Test 12: Tests that Housekeeping Staff cannot update maintenance status.
def test_housekeeping_staff_cannot_update_maintenance_status(client, room_test_data):

    # Create a maintenance report.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data
    )

    # Log in as Housekeeping Staff.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Housekeeper"
        session["role"] = "Housekeeping Staff"

    # Try to update the maintenance status.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "In Progress"}
    )

    # Access should be denied.
    assert response.status_code == 403

# Test 13: Tests that unauthenticated users cannot update maintenance status.
def test_unauthenticated_user_cannot_update_maintenance_status(client):

    # Try to update a maintenance report without logging in.
    response = client.post(
        "/update-maintenance-status/1",
        data={"maintenance_status": "In Progress"},
        follow_redirects=False
    )

    # The user should be redirected to staff login.
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/staff-login")

# Test 14: Tests that an invalid maintenance status cannot be submitted.
def test_invalid_maintenance_status_update(client, room_test_data):

    # Create a maintenance report.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data
    )

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Try to update the report with an invalid status.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "Completed"}
    )

    # The request should be rejected.
    assert response.status_code == 400

# Test 15: Tests that updating a non-existing maintenance report returns 404.
def test_update_nonexistent_maintenance_report(client):

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Try to update a report that does not exist.
    response = client.post(
        "/update-maintenance-status/9999",
        data={"maintenance_status": "In Progress"}
    )

    # The report should not be found.
    assert response.status_code == 404

# Test 16: Tests that a Reported issue cannot directly become Resolved.
def test_reported_issue_cannot_be_directly_resolved(client, room_test_data):

    # Create a maintenance report with Reported status.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data,
        report_status="Reported"
    )

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Try to directly resolve the report.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "Resolved"}
    )

    # The transition should be rejected.
    assert response.status_code == 400

# Test 17: Tests that an Administrator can change Reported status to In Progress.
def test_admin_can_update_reported_to_in_progress(client, room_test_data):

    from app import get_db_connection

    # Create a maintenance report.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data
    )

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Update the maintenance status.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "In Progress"},
        follow_redirects=False
    )

    # The request should redirect to the maintenance dashboard.
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/maintenance-dashboard")

    # Verify the updated status in the database.
    connection = get_db_connection()
    report = connection.execute("""
        SELECT maintenance_status
        FROM maintenance_reports
        WHERE report_id = ?
    """, (report_id,)).fetchone()
    connection.close()

    assert report["maintenance_status"] == "In Progress"

# Test 18: Tests that a Receptionist can change In Progress status to Resolved.
def test_receptionist_can_update_in_progress_to_resolved(client, room_test_data):

    from app import get_db_connection

    # Create a maintenance report with In Progress status.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data,
        report_status="In Progress"
    )

    # Log in as Receptionist.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Receptionist"
        session["role"] = "Receptionist"

    # Resolve the maintenance report.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "Resolved"},
        follow_redirects=False
    )

    # The request should redirect to the maintenance dashboard.
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/maintenance-dashboard")

    # Verify that the report is Resolved and resolved_at is recorded.
    connection = get_db_connection()

    report = connection.execute("""
        SELECT maintenance_status, resolved_at
        FROM maintenance_reports
        WHERE report_id = ?
    """, (report_id,)).fetchone()

    # Verify that the room is now Operational.
    room = connection.execute("""
        SELECT maintenance_status
        FROM rooms
        WHERE room_id = ?
    """, (room_id,)).fetchone()

    connection.close()

    assert report["maintenance_status"] == "Resolved"
    assert report["resolved_at"] is not None
    assert room["maintenance_status"] == "Operational"

# Test 19: Tests that an In Progress issue cannot be changed back to Reported.
def test_in_progress_issue_cannot_be_changed_back_to_reported(client, room_test_data):

    # Create a maintenance report with In Progress status.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data,
        report_status="In Progress"
    )

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Try to change the status back to Reported.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "Reported"}
    )

    # The transition should be rejected.
    assert response.status_code == 400

# Test 20: Tests that a room remains Under Maintenance if another report is unresolved.
def test_room_remains_under_maintenance_if_other_reports_are_unresolved(
    client, room_test_data
):

    from app import get_db_connection

    # Create the first maintenance report.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data,
        report_status="In Progress"
    )

    # Create a second unresolved report for the same room.
    connection = get_db_connection()

    connection.execute("""
        INSERT INTO maintenance_reports (
            room_id, reported_by, issue_description,
            reported_at, maintenance_status
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
    """, (
        room_id,
        user_id,
        "Another unresolved maintenance issue.",
        "Reported"
    ))

    connection.commit()
    connection.close()

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Resolve the first report.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "Resolved"}
    )

    assert response.status_code == 302

    # Verify that the room remains Under Maintenance.
    connection = get_db_connection()
    room = connection.execute("""
        SELECT maintenance_status
        FROM rooms
        WHERE room_id = ?
    """, (room_id,)).fetchone()
    connection.close()

    assert room["maintenance_status"] == "Under Maintenance"

# Test 21: Tests that a room becomes Operational after all its reports are resolved.
def test_room_becomes_operational_after_all_reports_are_resolved(
    client, room_test_data
):

    from app import get_db_connection

    # Create a maintenance report with In Progress status.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data,
        report_status="In Progress"
    )

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Resolve the only outstanding maintenance report.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "Resolved"}
    )

    assert response.status_code == 302

    # Verify that the room is now Operational.
    connection = get_db_connection()
    room = connection.execute("""
        SELECT maintenance_status
        FROM rooms
        WHERE room_id = ?
    """, (room_id,)).fetchone()
    connection.close()

    assert room["maintenance_status"] == "Operational"

# Test 22: Tests that an already Resolved maintenance report cannot be updated again.
def test_already_resolved_report_cannot_be_updated(client, room_test_data):

    from app import get_db_connection

    # Create a maintenance report that is already Resolved.
    user_id, report_id, room_id = create_test_maintenance_report(
        room_test_data,
        report_status="Resolved"
    )

    # Log in as Administrator.
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Try to update the already resolved report.
    response = client.post(
        f"/update-maintenance-status/{report_id}",
        data={"maintenance_status": "In Progress"}
    )

    # The request should be rejected.
    assert response.status_code == 400
