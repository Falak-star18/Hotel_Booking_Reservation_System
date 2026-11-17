# Test 1: Tests that staff must log in before accessing the housekeeping dashboard.
def test_housekeeping_dashboard_requires_login(client):

    response = client.get(
        "/housekeeping-dashboard",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert "/staff-login" in response.headers["Location"]

# Test 2: Tests that Administrator, Receptionist and Housekeeping Staff can view the housekeeping dashboard.
def test_all_staff_roles_can_view_housekeeping_dashboard(client, room_test_data):

    staff_roles = [
        "Administrator",
        "Receptionist",
        "Housekeeping Staff"
    ]

    for role in staff_roles:

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["role"] = role

        response = client.get("/housekeeping-dashboard")

        assert response.status_code == 200

# Test 3: Tests that Administrator and Receptionist cannot start room cleaning.
def test_admin_and_receptionist_cannot_start_cleaning(client, room_test_data):
    from app import get_db_connection

    connection = get_db_connection()

    room = connection.execute(
        "SELECT room_id FROM rooms WHERE room_number = ?",
        (room_test_data["room_number"],)
    ).fetchone()

    room_id = room["room_id"]

    # Set the room to Dirty/Vacant so cleaning can be started.
    connection.execute(
        """
        UPDATE rooms
        SET housekeeping_status = 'Dirty/Vacant'
        WHERE room_id = ?
        """,
        (room_id,)
    )

    connection.commit()
    connection.close()

    staff_roles = ["Administrator", "Receptionist"]

    for role in staff_roles:

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["role"] = role

        response = client.post(
            f"/start-cleaning/{room_id}"
        )

        assert response.status_code == 403

    # Verify that the room status was not changed.
    connection = get_db_connection()

    room = connection.execute(
        "SELECT housekeeping_status FROM rooms WHERE room_id = ?",
        (room_id,)
    ).fetchone()

    assert room["housekeeping_status"] == "Dirty/Vacant"

    connection.close()

# Test 4: Tests that Housekeeping Staff can start cleaning a room.
def test_housekeeping_staff_can_start_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    # Retrieve the test room
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

    # Create an actual housekeeping staff user.
    # This prevents the foreign key constraint error.
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
            "Test Housekeeping Staff",
            "test_housekeeping@example.com",
            "test_password_hash",
            "Housekeeping Staff"
        )
    )

    housekeeping_user_id = cursor.lastrowid

    # Set the room to Dirty/Vacant
    connection.execute(
        """
        UPDATE rooms
        SET housekeeping_status = 'Dirty/Vacant',
            maintenance_status = 'Operational'
        WHERE room_id = ?
        """,
        (room_id,)
    )

    connection.commit()
    connection.close()

    # Log in as the housekeeping staff member
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Staff"
        session["role"] = "Housekeeping Staff"

    # Start cleaning
    response = client.post(
        f"/start-cleaning/{room_id}",
        follow_redirects=False
    )

    # Check successful redirection
    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/housekeeping-dashboard"
    )

    connection = get_db_connection()

    try:
        # Verify room housekeeping status
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == (
            "Cleaning In Progress"
        )

        # Verify housekeeping assignment was created
        assignment = connection.execute(
            """
            SELECT room_id, assigned_to, cleaning_status
            FROM housekeeping_assignments
            WHERE room_id = ?
            ORDER BY assignment_id DESC
            LIMIT 1
            """,
            (room_id,)
        ).fetchone()

        assert assignment is not None
        assert assignment["room_id"] == room_id
        assert assignment["assigned_to"] == housekeeping_user_id
        assert assignment["cleaning_status"] == (
            "Cleaning In Progress"
        )

    finally:
        connection.close()

# Test 5: Test that only Housekeeping Staff can complete cleaning
def test_housekeeping_staff_can_complete_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    # Retrieve the test room
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

    # Create an actual housekeeping staff user
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
            "Test Housekeeping Staff",
            "test_housekeeping_complete@example.com",
            "test_password_hash",
            "Housekeeping Staff"
        )
    )

    housekeeping_user_id = cursor.lastrowid

    # Set room status to Cleaning In Progress
    connection.execute(
        """
        UPDATE rooms
        SET housekeeping_status = 'Cleaning In Progress',
            maintenance_status = 'Operational'
        WHERE room_id = ?
        """,
        (room_id,)
    )

    # Create an active housekeeping assignment
    connection.execute(
        """
        INSERT INTO housekeeping_assignments (
            room_id,
            assigned_to,
            assigned_date,
            started_at,
            cleaning_status
        )
        VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP, ?)
        """,
        (
            room_id,
            housekeeping_user_id,
            "Cleaning In Progress"
        )
    )

    connection.commit()
    connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Staff"
        session["role"] = "Housekeeping Staff"

    # Complete room cleaning
    response = client.post(
        f"/complete-cleaning/{room_id}",
        follow_redirects=False
    )

    # Verify successful redirection
    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/housekeeping-dashboard"
    )

    connection = get_db_connection()

    try:
        # Verify room status is updated
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == "Clean/Ready"

        # Verify housekeeping assignment is completed
        assignment = connection.execute(
            """
            SELECT cleaning_status, completed_at
            FROM housekeeping_assignments
            WHERE room_id = ?
            ORDER BY assignment_id DESC
            LIMIT 1
            """,
            (room_id,)
        ).fetchone()

        assert assignment is not None
        assert assignment["cleaning_status"] == "Completed"
        assert assignment["completed_at"] is not None

    finally:
        connection.close()

# Test 6: Receptionist cannot complete room cleaning
def test_receptionist_cannot_complete_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    # Retrieve the test room
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

    # Set room status to Cleaning In Progress
    connection.execute(
        """
        UPDATE rooms
        SET housekeeping_status = 'Cleaning In Progress',
            maintenance_status = 'Operational'
        WHERE room_id = ?
        """,
        (room_id,)
    )

    connection.commit()
    connection.close()

    # Log in as Receptionist
    with client.session_transaction() as session:
        session["user_id"] = 999
        session["full_name"] = "Test Receptionist"
        session["role"] = "Receptionist"

    # Try to complete room cleaning
    response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    # Receptionist should be denied access
    assert response.status_code == 403

    # Verify room status remains unchanged
    connection = get_db_connection()

    try:
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == (
            "Cleaning In Progress"
        )

    finally:
        connection.close()

# Test 7: Administrator cannot complete room cleaning.
def test_admin_cannot_complete_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    # Retrieve the test room
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

    # Set room status to Cleaning In Progress
    connection.execute(
        """
        UPDATE rooms
        SET housekeeping_status = 'Cleaning In Progress',
            maintenance_status = 'Operational'
        WHERE room_id = ?
        """,
        (room_id,)
    )

    connection.commit()
    connection.close()

    # Log in as Administrator
    with client.session_transaction() as session:
        session["user_id"] = 999
        session["full_name"] = "Test Administrator"
        session["role"] = "Administrator"

    # Try to complete room cleaning
    response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    # Administrator should be denied access
    assert response.status_code == 403

    # Verify room status remains unchanged
    connection = get_db_connection()

    try:
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == (
            "Cleaning In Progress"
        )

    finally:
        connection.close()

# Test 8: Unauthenticated users cannot complete room cleaning.
def test_unauthenticated_user_cannot_complete_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    # Retrieve the test room
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

    # Set room status to Cleaning In Progress
    connection.execute(
        """
        UPDATE rooms
        SET housekeeping_status = 'Cleaning In Progress',
            maintenance_status = 'Operational'
        WHERE room_id = ?
        """,
        (room_id,)
    )

    connection.commit()
    connection.close()

    # Do not create a login session

    # Try to complete room cleaning
    response = client.post(
        f"/complete-cleaning/{room_id}",
        follow_redirects=False
    )

    # User should be redirected to staff login
    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/staff-login"
    )

    # Verify room status remains unchanged
    connection = get_db_connection()

    try:
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == (
            "Cleaning In Progress"
        )

    finally:
        connection.close()

# Test 9: Room requiring repair cannot be marked Clean/Ready.
def test_room_needing_repair_cannot_complete_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    # Retrieve the test room
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

    # Create a housekeeping staff user
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
            "Test Housekeeping Repair",
            "test_housekeeping_repair@example.com",
            "test_password_hash",
            "Housekeeping Staff"
        )
    )

    housekeeping_user_id = cursor.lastrowid

    # Set room to Cleaning In Progress but mark it as needing repair
    connection.execute(
    """
    UPDATE rooms
    SET housekeeping_status = 'Cleaning In Progress',
        maintenance_status = 'Under Maintenance'
    WHERE room_id = ?
    """,
    (room_id,)
)

    # Create an active housekeeping assignment
    connection.execute(
        """
        INSERT INTO housekeeping_assignments (
            room_id,
            assigned_to,
            assigned_date,
            started_at,
            cleaning_status
        )
        VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP, ?)
        """,
        (
            room_id,
            housekeeping_user_id,
            "Cleaning In Progress"
        )
    )

    connection.commit()
    connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Repair"
        session["role"] = "Housekeeping Staff"

    # Try to complete cleaning
    response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    # Route should redirect, but should not update the room
    assert response.status_code == 302

    # Verify room and assignment remain unchanged
    connection = get_db_connection()

    try:
        updated_room = connection.execute(
            """
            SELECT housekeeping_status, maintenance_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == (
            "Cleaning In Progress"
        )
        assert updated_room["maintenance_status"] == "Under Maintenance"

        assignment = connection.execute(
            """
            SELECT cleaning_status, completed_at
            FROM housekeeping_assignments
            WHERE room_id = ?
            ORDER BY assignment_id DESC
            LIMIT 1
            """,
            (room_id,)
        ).fetchone()

        assert assignment["cleaning_status"] == (
            "Cleaning In Progress"
        )
        assert assignment["completed_at"] is None

    finally:
        connection.close()

# Test 10: Tests whether a room under maintenance cannot be started for cleaning.
def test_room_under_maintenance_cannot_start_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Create a Housekeeping Staff user
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
                "Test Housekeeping Maintenance",
                "test_housekeeping_maintenance@example.com",
                "test_password_hash",
                "Housekeeping Staff"
            )
        )

        housekeeping_user_id = cursor.lastrowid

        # Set room as Dirty/Vacant but Under Maintenance
        connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Dirty/Vacant',
                maintenance_status = 'Under Maintenance'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        connection.commit()

    finally:
        connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Maintenance"
        session["role"] = "Housekeeping Staff"

    # Try to start cleaning
    response = client.post(
        f"/start-cleaning/{room_id}"
    )

    # Route should redirect without starting cleaning
    assert response.status_code == 302

    # Verify room status and maintenance status remain unchanged
    connection = get_db_connection()

    try:
        updated_room = connection.execute(
            """
            SELECT housekeeping_status, maintenance_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == "Dirty/Vacant"
        assert updated_room["maintenance_status"] == "Under Maintenance"

        # Verify no housekeeping assignment was created
        assignment = connection.execute(
            """
            SELECT assignment_id
            FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert assignment is None

    finally:
        connection.close()

# Test 11: Tests that cleaning cannot be started again for a room already being cleaned.
def test_cannot_start_cleaning_for_room_already_in_progress(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Create a Housekeeping Staff user
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
                "Test Housekeeping Duplicate",
                "test_housekeeping_duplicate@example.com",
                "test_password_hash",
                "Housekeeping Staff"
            )
        )

        housekeeping_user_id = cursor.lastrowid

        # Remove previous assignments for a clean test
        connection.execute(
            """
            DELETE FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Set room status to Cleaning In Progress
        connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Cleaning In Progress',
                maintenance_status = 'Operational'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Create an existing active housekeeping assignment
        connection.execute(
            """
            INSERT INTO housekeeping_assignments (
                room_id,
                assigned_to,
                assigned_date,
                started_at,
                cleaning_status
            )
            VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP, ?)
            """,
            (
                room_id,
                housekeeping_user_id,
                "Cleaning In Progress"
            )
        )

        connection.commit()

    finally:
        connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Duplicate"
        session["role"] = "Housekeeping Staff"

    # Try to start cleaning the same room again
    response = client.post(
        f"/start-cleaning/{room_id}"
    )

    # Route should redirect without creating another assignment
    assert response.status_code == 302

    connection = get_db_connection()

    try:
        # Verify room status remains unchanged
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == (
            "Cleaning In Progress"
        )

        # Verify no duplicate housekeeping assignment was created
        assignments = connection.execute(
            """
            SELECT assignment_id, cleaning_status
            FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchall()

        assert len(assignments) == 1

        assert assignments[0]["cleaning_status"] == (
            "Cleaning In Progress"
        )

    finally:
        connection.close()

# Test 12: Tests that cleaning cannot be completed without an active housekeeping assignment.
def test_cannot_complete_cleaning_without_active_assignment(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Create a Housekeeping Staff user
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
                "Test Housekeeping No Assignment",
                "test_housekeeping_no_assignment@example.com",
                "test_password_hash",
                "Housekeeping Staff"
            )
        )

        housekeeping_user_id = cursor.lastrowid

        # Remove existing housekeeping assignments
        connection.execute(
            """
            DELETE FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Set room to Cleaning In Progress
        # without creating a housekeeping assignment
        connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Cleaning In Progress',
                maintenance_status = 'Operational'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        connection.commit()

    finally:
        connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping No Assignment"
        session["role"] = "Housekeeping Staff"

    # Try to complete cleaning without an active assignment
    response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    # Route should redirect without completing cleaning
    assert response.status_code == 302

    connection = get_db_connection()

    try:
        # Verify room status remains unchanged
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == (
            "Cleaning In Progress"
        )

        # Verify no housekeeping assignment exists
        assignment = connection.execute(
            """
            SELECT assignment_id
            FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert assignment is None

    finally:
        connection.close()

# Test 13: Tests that unauthenticated users cannot start room cleaning.
def test_unauthenticated_user_cannot_start_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Set room to Dirty/Vacant and Operational
        connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Dirty/Vacant',
                maintenance_status = 'Operational'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Remove existing housekeeping assignments
        connection.execute(
            """
            DELETE FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        )

        connection.commit()

    finally:
        connection.close()

    # Do not create a login session

    # Try to start cleaning without logging in
    response = client.post(
        f"/start-cleaning/{room_id}",
        follow_redirects=False
    )

    # User should be redirected to staff login
    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/staff-login"
    )

    connection = get_db_connection()

    try:
        # Verify room status remains unchanged
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == "Dirty/Vacant"

        # Verify no housekeeping assignment was created
        assignment = connection.execute(
            """
            SELECT assignment_id
            FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert assignment is None

    finally:
        connection.close()

# Test 14: Tests that Housekeeping Staff cannot start cleaning an inactive room.
def test_inactive_room_cannot_start_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Create a Housekeeping Staff user
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
                "Test Housekeeping Inactive",
                "test_housekeeping_inactive@example.com",
                "test_password_hash",
                "Housekeeping Staff"
            )
        )

        housekeeping_user_id = cursor.lastrowid

        # Remove existing housekeeping assignments
        connection.execute(
            """
            DELETE FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Set the room as inactive
        connection.execute(
            """
            UPDATE rooms
            SET is_active = 0,
                housekeeping_status = 'Dirty/Vacant',
                maintenance_status = 'Operational'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        connection.commit()

    finally:
        connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Inactive"
        session["role"] = "Housekeeping Staff"

    # Try to start cleaning the inactive room
    response = client.post(
        f"/start-cleaning/{room_id}"
    )

    # Route should redirect without starting cleaning
    assert response.status_code == 302

    connection = get_db_connection()

    try:
        # Verify room remains inactive and Dirty/Vacant
        updated_room = connection.execute(
            """
            SELECT is_active, housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["is_active"] == 0
        assert updated_room["housekeeping_status"] == "Dirty/Vacant"

        # Verify no housekeeping assignment was created
        assignment = connection.execute(
            """
            SELECT assignment_id
            FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert assignment is None

    finally:
        connection.close()

# Test 15: Tests that an inactive room cannot complete cleaning.
def test_inactive_room_cannot_complete_cleaning(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Create a Housekeeping Staff user
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
                "Test Housekeeping Inactive Complete",
                "test_housekeeping_inactive_complete@example.com",
                "test_password_hash",
                "Housekeeping Staff"
            )
        )

        housekeeping_user_id = cursor.lastrowid

        # Remove existing assignments
        connection.execute(
            """
            DELETE FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Set room as inactive but Cleaning In Progress
        connection.execute(
            """
            UPDATE rooms
            SET is_active = 0,
                housekeeping_status = 'Cleaning In Progress',
                maintenance_status = 'Operational'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Create an active housekeeping assignment
        connection.execute(
            """
            INSERT INTO housekeeping_assignments (
                room_id,
                assigned_to,
                assigned_date,
                started_at,
                cleaning_status
            )
            VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP, ?)
            """,
            (
                room_id,
                housekeeping_user_id,
                "Cleaning In Progress"
            )
        )

        connection.commit()

    finally:
        connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Inactive Complete"
        session["role"] = "Housekeeping Staff"

    # Try to complete cleaning
    response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    # Route should redirect without completing cleaning
    assert response.status_code == 302

    connection = get_db_connection()

    try:
        # Verify room remains inactive and cleaning is incomplete
        updated_room = connection.execute(
            """
            SELECT is_active, housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["is_active"] == 0
        assert updated_room["housekeeping_status"] == (
            "Cleaning In Progress"
        )

        # Verify assignment remains incomplete
        assignment = connection.execute(
            """
            SELECT cleaning_status, completed_at
            FROM housekeeping_assignments
            WHERE room_id = ?
            ORDER BY assignment_id DESC
            LIMIT 1
            """,
            (room_id,)
        ).fetchone()

        assert assignment is not None
        assert assignment["cleaning_status"] == (
            "Cleaning In Progress"
        )
        assert assignment["completed_at"] is None

    finally:
        connection.close()

# Test 16: Tests that cleaning cannot be completed if the room is not in Cleaning In Progress status.
def test_cannot_complete_cleaning_if_room_is_not_in_progress(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Create a Housekeeping Staff user
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
                "Test Housekeeping Invalid Status",
                "test_housekeeping_invalid_status@example.com",
                "test_password_hash",
                "Housekeeping Staff"
            )
        )

        housekeeping_user_id = cursor.lastrowid

        # Remove existing assignments
        connection.execute(
            """
            DELETE FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Set room to Dirty/Vacant
        connection.execute(
            """
            UPDATE rooms
            SET is_active = 1,
                housekeeping_status = 'Dirty/Vacant',
                maintenance_status = 'Operational'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Create an active housekeeping assignment
        connection.execute(
            """
            INSERT INTO housekeeping_assignments (
                room_id,
                assigned_to,
                assigned_date,
                started_at,
                cleaning_status
            )
            VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP, ?)
            """,
            (
                room_id,
                housekeeping_user_id,
                "Cleaning In Progress"
            )
        )

        connection.commit()

    finally:
        connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Invalid Status"
        session["role"] = "Housekeeping Staff"

    # Try to complete cleaning
    response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    # Route should redirect without completing cleaning
    assert response.status_code == 302

    connection = get_db_connection()

    try:
        # Verify room status remains unchanged
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == "Dirty/Vacant"

        # Verify assignment remains incomplete
        assignment = connection.execute(
            """
            SELECT cleaning_status, completed_at
            FROM housekeeping_assignments
            WHERE room_id = ?
            ORDER BY assignment_id DESC
            LIMIT 1
            """,
            (room_id,)
        ).fetchone()

        assert assignment is not None
        assert assignment["cleaning_status"] == (
            "Cleaning In Progress"
        )
        assert assignment["completed_at"] is None

    finally:
        connection.close()

# Test 17: Tests that cleaning cannot be completed again if the room is already Clean/Ready.
def test_cannot_complete_cleaning_if_room_is_already_ready(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Create a Housekeeping Staff user
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
                "Test Housekeeping Already Ready",
                "test_housekeeping_already_ready@example.com",
                "test_password_hash",
                "Housekeeping Staff"
            )
        )

        housekeeping_user_id = cursor.lastrowid

        # Remove existing assignments
        connection.execute(
            """
            DELETE FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Set room as Clean/Ready
        connection.execute(
            """
            UPDATE rooms
            SET is_active = 1,
                housekeeping_status = 'Clean/Ready',
                maintenance_status = 'Operational'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Create an active housekeeping assignment
        connection.execute(
            """
            INSERT INTO housekeeping_assignments (
                room_id,
                assigned_to,
                assigned_date,
                started_at,
                cleaning_status
            )
            VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP, ?)
            """,
            (
                room_id,
                housekeeping_user_id,
                "Cleaning In Progress"
            )
        )

        connection.commit()

    finally:
        connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Already Ready"
        session["role"] = "Housekeeping Staff"

    # Try to complete cleaning again
    response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    # Route should redirect without processing completion
    assert response.status_code == 302

    connection = get_db_connection()

    try:
        # Verify room remains Clean/Ready
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == "Clean/Ready"

        # Verify assignment remains unchanged
        assignment = connection.execute(
            """
            SELECT cleaning_status, completed_at
            FROM housekeeping_assignments
            WHERE room_id = ?
            ORDER BY assignment_id DESC
            LIMIT 1
            """,
            (room_id,)
        ).fetchone()

        assert assignment is not None
        assert assignment["cleaning_status"] == (
            "Cleaning In Progress"
        )
        assert assignment["completed_at"] is None

    finally:
        connection.close()

# Test 18: Tests that completing cleaning updates the correct active housekeeping assignment.
def test_completing_cleaning_updates_correct_assignment(
    client, room_test_data
):
    from app import get_db_connection

    connection = get_db_connection()

    try:
        # Retrieve the test room
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

        # Create a Housekeeping Staff user
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
                "Test Housekeeping Assignment",
                "test_housekeeping_assignment@example.com",
                "test_password_hash",
                "Housekeeping Staff"
            )
        )

        housekeeping_user_id = cursor.lastrowid

        # Remove existing assignments
        connection.execute(
            """
            DELETE FROM housekeeping_assignments
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Set room to Cleaning In Progress
        connection.execute(
            """
            UPDATE rooms
            SET is_active = 1,
                housekeeping_status = 'Cleaning In Progress',
                maintenance_status = 'Operational'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        # Create a previous completed assignment
        connection.execute(
            """
            INSERT INTO housekeeping_assignments (
                room_id,
                assigned_to,
                assigned_date,
                started_at,
                cleaning_status,
                completed_at
            )
            VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
            """,
            (
                room_id,
                housekeeping_user_id,
                "Completed"
            )
        )

        # Create a new active housekeeping assignment
        connection.execute(
            """
            INSERT INTO housekeeping_assignments (
                room_id,
                assigned_to,
                assigned_date,
                started_at,
                cleaning_status
            )
            VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP, ?)
            """,
            (
                room_id,
                housekeeping_user_id,
                "Cleaning In Progress"
            )
        )

        connection.commit()

    finally:
        connection.close()

    # Log in as Housekeeping Staff
    with client.session_transaction() as session:
        session["user_id"] = housekeeping_user_id
        session["full_name"] = "Test Housekeeping Assignment"
        session["role"] = "Housekeeping Staff"

    # Complete room cleaning
    response = client.post(
        f"/complete-cleaning/{room_id}"
    )

    # Verify successful redirection
    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/housekeeping-dashboard"
    )

    connection = get_db_connection()

    try:
        # Verify room is Clean/Ready
        updated_room = connection.execute(
            """
            SELECT housekeeping_status
            FROM rooms
            WHERE room_id = ?
            """,
            (room_id,)
        ).fetchone()

        assert updated_room["housekeeping_status"] == "Clean/Ready"

        # Retrieve both housekeeping assignments
        assignments = connection.execute(
            """
            SELECT cleaning_status, completed_at
            FROM housekeeping_assignments
            WHERE room_id = ?
            ORDER BY assignment_id ASC
            """,
            (room_id,)
        ).fetchall()

        assert len(assignments) == 2

        # Previous assignment should remain completed
        assert assignments[0]["cleaning_status"] == "Completed"
        assert assignments[0]["completed_at"] is not None

        # Current active assignment should now be completed
        assert assignments[1]["cleaning_status"] == "Completed"
        assert assignments[1]["completed_at"] is not None

    finally:
        connection.close()
