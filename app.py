# ----------------------------------------
# 1. Import Flask
# ----------------------------------------

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import uuid
import sqlite3
import bcrypt
import secrets
import json
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

# Breezy Palms PDF Fonts
BASE_DIR = Path(__file__).resolve().parent
FONT_DIR = BASE_DIR / "static" / "fonts"

pdfmetrics.registerFont(
    TTFont("Poppins-Bold", str(FONT_DIR / "Poppins-Bold.ttf"))
)

pdfmetrics.registerFont(
    TTFont("DancingScript", str(FONT_DIR / "DancingScript-Regular.ttf"))
)

# ----------------------------------------
# Import Database Connection
# ----------------------------------------

from database.db import get_db_connection

# ----------------------------------------
# 2. Create Flask Application
# ----------------------------------------

app = Flask(__name__)
app.secret_key = "our-hotel-development-secret-key-2026"

def expire_pending_bookings():
    connection = get_db_connection()

    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        connection.execute("BEGIN IMMEDIATE")

        # Mark expired pending bookings
        connection.execute(
            """
            UPDATE pending_bookings
            SET status = 'Expired'
            WHERE status = 'Pending'
              AND expires_at <= ?
            """,
            (current_time,)
        )

        # Release holds belonging to expired bookings
        connection.execute(
            """
            DELETE FROM room_holds
            WHERE EXISTS (
                SELECT 1
                FROM pending_bookings
                WHERE pending_bookings.room_id = room_holds.room_id
                  AND pending_bookings.guest_id = room_holds.guest_id
                  AND pending_bookings.checkin_date = room_holds.checkin_date
                  AND pending_bookings.checkout_date = room_holds.checkout_date
                  AND pending_bookings.status = 'Expired'
            )
            AND hold_expires_at <= ?
            """,
            (current_time,)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

# Guest Login Page
@app.route("/guest-login", methods=["GET", "POST"])
def guest_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db_connection()

        guest = connection.execute(
            """
            SELECT guest_id, full_name, email, password_hash
            FROM guests
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        connection.close()

        if guest is None or guest["password_hash"] is None:
            flash("Invalid email or password.", "error")
            return redirect(url_for("guest_login"))

        if not bcrypt.checkpw(
            password.encode("utf-8"),
            guest["password_hash"].encode("utf-8")
        ):
            flash("Invalid email or password.", "error")
            return redirect(url_for("guest_login"))
        
        session["guest_id"] = guest["guest_id"]
        session["guest_name"] = guest["full_name"]
        session["guest_email"] = guest["email"]

        return redirect(url_for("home"))

    return render_template("guest_login.html")

# Guest Logout
@app.route("/guest-logout")
def guest_logout():
    session.clear()

    return redirect(url_for("home"))

# Guest My Bookings
@app.route("/my-bookings")
def my_bookings():

    # Check whether the guest is logged in
    if "guest_id" not in session:
        flash("Please log in to view your bookings.", "error")
        return redirect(url_for("guest_login"))

    connection = get_db_connection()

    try:
        bookings = connection.execute(
            """
            SELECT
                r.reservation_id,
                r.booking_reference,
                r.checkin_date,
                r.checkout_date,
                r.number_of_guests,
                r.booking_status,
                r.total_amount,
                r.payment_status,
                rm.room_number,
                rc.category_name
            FROM reservations r
            JOIN rooms rm
                ON r.room_id = rm.room_id
            JOIN room_categories rc
                ON rm.category_id = rc.category_id
            WHERE r.guest_id = ?
            ORDER BY r.created_at DESC
            """,
            (session["guest_id"],)
        ).fetchall()

        return render_template(
            "my_bookings.html",
            bookings=bookings,
            guest_name=session.get("guest_name")
        )

    finally:
        connection.close()

# Guest Booking Cancellation
@app.route("/cancel-booking/<int:reservation_id>", methods=["POST"])
def cancel_booking(reservation_id):

    # Check whether the guest is logged in
    if "guest_id" not in session:
        flash("Please log in to cancel a booking.", "error")
        return redirect(url_for("guest_login"))

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        # Retrieve the guest's booking and successful payment
        booking = connection.execute(
            """
            SELECT
                r.reservation_id,
                r.checkin_date,
                r.total_amount,
                r.booking_status,
                r.payment_status,
                p.payment_id
            FROM reservations r
            JOIN payments p
                ON r.reservation_id = p.reservation_id
            WHERE r.reservation_id = ?
              AND r.guest_id = ?
              AND p.payment_status = 'Successful'
            ORDER BY p.transaction_date DESC
            LIMIT 1
            """,
            (reservation_id, session["guest_id"])
        ).fetchone()

        if booking is None:
            connection.rollback()
            flash("Booking not found or successful payment not available.", "error")
            return redirect(url_for("my_bookings"))

        if booking["booking_status"] != "Confirmed":
            connection.rollback()
            flash("This booking cannot be cancelled.", "error")
            return redirect(url_for("my_bookings"))

        # Calculate hours remaining until check-in
        checkin_datetime = datetime.strptime(
            booking["checkin_date"], "%Y-%m-%d"
        )

        current_datetime = datetime.now()

        # Prevent cancellation on or after the check-in date
        if current_datetime.date() >= checkin_datetime.date():
            connection.rollback()
            flash("Bookings cannot be cancelled on or after the check-in date.", "error")
            return redirect(url_for("my_bookings"))

        days_remaining = (
            checkin_datetime.date() - current_datetime.date()
        ).days

        if days_remaining >= 3:
            refund_percentage = 100
        elif days_remaining == 2:
            refund_percentage = 50
        else:
            refund_percentage = 0

        refund_amount = (
            booking["total_amount"] * refund_percentage / 100
        )

        # Record the simulated refund
        refund_status = (
            "Processed" if refund_percentage > 0 else "Not Eligible"
        )

        # Check whether a refund record already exists
        existing_refund = connection.execute(
            """
            SELECT refund_id
            FROM refunds
            WHERE reservation_id = ?
            """,
           (reservation_id,)
        ).fetchone()

        if existing_refund is not None:
            connection.rollback()
            flash("A cancellation record already exists for this booking.", "error")
            return redirect(url_for("my_bookings"))

        connection.execute(
            """
            INSERT INTO refunds (
                payment_id,
                reservation_id,
                cancellation_time,
                refund_percentage,
                refund_amount,
                refund_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                booking["payment_id"],
                reservation_id,
                current_datetime.isoformat(timespec="seconds"),
                refund_percentage,
                refund_amount,
                refund_status
            )
        )

        # Update payment status
        if refund_percentage == 100:
            payment_status = "Refunded"
        elif refund_percentage == 50:
            payment_status = "Partially Refunded"
        else:
            payment_status = "No Refund"

        connection.execute(
            """
            UPDATE payments
            SET payment_status = ?
            WHERE payment_id = ?
            """,
            (payment_status, booking["payment_id"])
        )

        connection.execute(
            """
            UPDATE reservations
            SET booking_status = 'Cancelled',
                payment_status = ?
            WHERE reservation_id = ?
              AND guest_id = ?
            """,
            (payment_status, reservation_id, session["guest_id"])
        )

        connection.commit()

        flash(
            f"Booking cancelled. Refund: {refund_percentage}% "
            f"(₹{refund_amount:.2f}).",
            "success"
        )

        return redirect(url_for("my_bookings"))

    except Exception:
        connection.rollback()
        flash("Something went wrong while cancelling the booking.", "error")
        raise

    finally:
        connection.close()

# Guest Registration
@app.route("/guest-register", methods=["GET", "POST"])
def guest_register():

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate required fields
        if not all([full_name, email, phone, password, confirm_password]):
            return "All fields are required.", 400

        # Validate phone number
        if not phone.isdigit() or len(phone) != 10:
            return "Please enter a valid 10-digit phone number.", 400

        # Validate password length
        if len(password) < 8:
            return "Password must contain at least 8 characters.", 400

        # Confirm password
        if password != confirm_password:
            return "Passwords do not match.", 400

        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        connection = get_db_connection()

        try:
            connection.execute(
                """
                INSERT INTO guests
                (full_name, email, phone, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (full_name, email, phone, password_hash)
            )

            connection.commit()

        except sqlite3.IntegrityError:
            connection.rollback()
            return "An account with this email already exists.", 409

        finally:
            connection.close()

        return redirect(url_for("guest_login"))

    return render_template("guest_register.html")

@app.route("/staff-login", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        connection = get_db_connection()

        try:
            user = connection.execute(
                """
                SELECT user_id, full_name, email, password_hash, role
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

        finally:
            connection.close()

        if user is None:
            return render_template(
                "staff_login.html",
                error="Invalid email or password."
            )

        stored_hash = user["password_hash"]

        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")

        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return render_template(
                "staff_login.html",
                error="Invalid email or password."
            )

        session["user_id"] = user["user_id"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        # Redirect staff members to their respective dashboards

        if user["role"] == "Administrator":
            return redirect(url_for("admin_dashboard"))

        elif user["role"] == "Receptionist":
            return redirect(url_for("receptionist_dashboard"))

        elif user["role"] == "Housekeeping Staff":
            return redirect(url_for("housekeeping_dashboard"))
        
        return render_template(
            "staff_login.html",
            error="Login successful. Your staff dashboard is being prepared."
        )

    return render_template("staff_login.html")

# ----------------------------------------
# 3. Define Homepage Route
# ----------------------------------------

@app.route("/")
def home():

    connection = get_db_connection()

    try:

        # Retrieve all room categories
        room_categories = connection.execute(
            """
            SELECT *
            FROM room_categories
            ORDER BY category_id
            """
        ).fetchall()

        # Display homepage with database information
        return render_template(
            "index.html",
            room_categories=room_categories,
            guest_name=session.get("guest_name")
        )

    finally:

        connection.close()

# ----------------------------------------
# Test Database Connection Route
# ----------------------------------------

@app.route("/test-db")
def test_database():

    connection = get_db_connection()

    try:

        categories = connection.execute(
            "SELECT * FROM room_categories"
        ).fetchall()

        return {
            "message": "Database connected successfully!",
            "total_room_categories": len(categories),
            "categories": [
                category["category_name"]
                for category in categories
            ]
        }

    finally:

        connection.close()

# ----------------------------------------
# 4. Check Room Availability Route
# ----------------------------------------

@app.route("/check-availability", methods=["POST"])
def check_availability():

    if "guest_id" not in session:
        flash("Please log in to check room availability.", "error")
        return redirect(url_for("guest_login"))
    
    checkin_date = request.form.get("checkin_date")
    checkout_date = request.form.get("checkout_date")
    guests = request.form.get("guests")
    category_id = request.form.get("category_id")

    # ----------------------------------------
    # Calculate Number of Nights
    # ----------------------------------------

    checkin = datetime.strptime(checkin_date, "%Y-%m-%d")
    checkout = datetime.strptime(checkout_date, "%Y-%m-%d")

    number_of_nights = (checkout - checkin).days

    # ----------------------------------------
    # Connect to Database
    # ----------------------------------------

    connection = get_db_connection()

    try:

        # ----------------------------------------
        # Clean Up Expired Pending Bookings
        # ----------------------------------------

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        connection.execute(
            """
            UPDATE pending_bookings
            SET status = 'Expired'
            WHERE status = 'Pending'
              AND expires_at <= ?
            """,
            (current_time,)
        )

        connection.execute(
            """
            DELETE FROM room_holds
            WHERE hold_expires_at <= ?
            """,
            (current_time,)
        )

        connection.commit()

        # Retrieve the selected room category
        selected_category = connection.execute(
            """
            SELECT category_name, minimum_guests,
                   maximum_guests, base_price
            FROM room_categories
            WHERE category_id = ?
            """,
            (category_id,)
        ).fetchone()

        if selected_category is None:
            return "Invalid room category selected!", 400

        # Retrieve the base room price
        base_price = selected_category["base_price"]

        # ----------------------------------------
        # Validate Number of Guests
        # ----------------------------------------

        number_of_guests = int(guests)

        if number_of_guests < selected_category["minimum_guests"]:
            return (
                f"This room requires at least "
                f"{selected_category['minimum_guests']} guests.",
                400
            )

        if number_of_guests > selected_category["maximum_guests"]:
            return (
                f"This room allows a maximum of "
                f"{selected_category['maximum_guests']} guests.",
                400
            )
        
        # ----------------------------------------
        # Check Actual Room Availability
        # ----------------------------------------

        available_rooms = connection.execute(
    """
    SELECT room_id, room_number
    FROM rooms
    WHERE category_id = ?
      AND is_active = 1
      AND maintenance_status = 'Operational'
      AND housekeeping_status = 'Clean/Ready'

      AND room_id NOT IN (
          SELECT room_id
          FROM reservations
          WHERE booking_status IN (
              'Confirmed',
              'Checked-in'
          )
          AND checkin_date < ?
          AND checkout_date > ?
      )

      AND room_id NOT IN (
          SELECT room_id
          FROM maintenance_reports
          WHERE maintenance_status != 'Resolved'
      )

            AND room_id NOT IN (
          SELECT room_id
          FROM room_holds
          WHERE hold_expires_at > ?
      )

    ORDER BY room_number
    """,
    (category_id, checkout_date, checkin_date, current_time)
).fetchall()

        available_room_count = len(available_rooms)

        # ----------------------------------------
        # Prepare Date-wise Pricing
        # ----------------------------------------

        nightly_rates = []
        total_amount = 0

        # ----------------------------------------
        # Calculate Price for Each Night
        # ----------------------------------------

        for day in range(number_of_nights):

            current_date = checkin + timedelta(days=day)

            current_month = current_date.month

            # Identify the season
            if current_month >= 11 or current_month <= 5:
                season_name = "Peak Season"
            else:
                season_name = "Normal Season"

            # Retrieve the seasonal multiplier
            season = connection.execute(
                """
                SELECT price_multiplier
                FROM seasons
                WHERE season_name = ?
                """,
                (season_name,)
            ).fetchone()

            if season is None:
                return "Seasonal pricing information not found!", 500

            season_multiplier = season["price_multiplier"]

            # Calculate nightly price
            nightly_price = base_price * season_multiplier

            # Add price to total
            total_amount += nightly_price

            # Store nightly pricing details
            nightly_rates.append({
                "stay_date": current_date.strftime("%Y-%m-%d"),
                "season_name": season_name,
                "season_multiplier": season_multiplier,
                "nightly_price": nightly_price
            })

        # ----------------------------------------
        # Display Availability Results
        # ----------------------------------------

        return render_template(
            "availability.html",
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            guests=guests,
            room_category=selected_category["category_name"],
            category_id=category_id,
            number_of_nights=number_of_nights,
            base_price=base_price,
            nightly_rates=nightly_rates,
            total_amount=total_amount,
            available_rooms=available_rooms,
            available_room_count=available_room_count
        )

    finally:
        connection.close()

# ----------------------------------------
# 5. Reservation Form Route
# ----------------------------------------

@app.route("/reservation", methods=["POST"])
def reservation():

        if "guest_id" not in session:
            flash("Please log in before making a reservation.", "error")
            return redirect(url_for("guest_login"))

        checkin_date = request.form.get("checkin_date")
        checkout_date = request.form.get("checkout_date")
        guests = request.form.get("guests")
        category_id = request.form.get("category_id")
        total_amount = request.form.get("total_amount")

        return render_template(
            "reservation.html",
             checkin_date=checkin_date,
             checkout_date=checkout_date,
             guests=guests,
             category_id=category_id,
             total_amount=total_amount,
             guest_name=session.get("guest_name"),
             guest_email=session.get("guest_email")
        )

# ----------------------------------------
# 6. Confirm Reservation Route
# ----------------------------------------

@app.route("/confirm-reservation", methods=["POST"])
def confirm_reservation():

    # Check guest login
    if "guest_id" not in session:
        flash("Please log in before confirming your reservation.", "error")
        return redirect(url_for("guest_login"))

    # Get booking details
    checkin_date = request.form.get("checkin_date")
    checkout_date = request.form.get("checkout_date")
    guests = request.form.get("guests")
    category_id = request.form.get("category_id")

    # Get primary guest details
    phone = request.form.get("phone")
    address = request.form.get("address")
    id_type = request.form.get("id_type")
    id_number = request.form.get("id_number")

    # Get occupant details
    occupant_names = request.form.getlist("occupant_name[]")
    occupant_ages = request.form.getlist("occupant_age[]")

    # Basic validation
    if not all([
        checkin_date,
        checkout_date,
        guests,
        category_id,
        phone,
        address,
        id_type,
        id_number
    ]):
        return "Please fill in all required fields.", 400

    # Validate phone number
    if not phone.isdigit() or len(phone) != 10:
        return "Please enter a valid 10-digit phone number.", 400

    try:
        checkin = datetime.strptime(checkin_date, "%Y-%m-%d")
        checkout = datetime.strptime(checkout_date, "%Y-%m-%d")
        number_of_guests = int(guests)
        category_id = int(category_id)

        if checkout <= checkin:
            return "Check-out must be after check-in.", 400

        if number_of_guests < 1:
            return "Invalid number of guests.", 400

        if (
            len(occupant_names) != number_of_guests
            or len(occupant_ages) != number_of_guests
        ):
            return "Please enter details for every occupant.", 400

        for name, age in zip(occupant_names, occupant_ages):

            if not name.strip():
                return "Every occupant must have a name.", 400

            if not age.isdigit() or not 1 <= int(age) <= 99:
                return "Please enter an age between 1 and 99 for every occupant.", 400

    except (ValueError, TypeError):
        return "Invalid booking details.", 400

    connection = get_db_connection()

    try:

        # Lock the database for this booking transaction
        connection.execute("BEGIN IMMEDIATE")

        # Retrieve the selected room category
        category = connection.execute(
            """
            SELECT *
            FROM room_categories
            WHERE category_id = ?
            """,
            (category_id,)
        ).fetchone()

        if category is None:
            connection.rollback()
            return "Invalid room category.", 400

        if not (
            category["minimum_guests"]
            <= number_of_guests
            <= category["maximum_guests"]
        ):
            connection.rollback()
            return "Guest count is outside the room capacity.", 400
        
                # Prevent duplicate pending bookings by the same guest
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        duplicate_booking = connection.execute(
            """
            SELECT pending_booking_id
            FROM pending_bookings
            WHERE guest_id = ?
              AND checkin_date = ?
              AND checkout_date = ?
              AND status = 'Pending'
              AND expires_at > ?
            LIMIT 1
            """,
            (
                session["guest_id"],
                checkin_date,
                checkout_date,
                current_time
            )
        ).fetchone()

        if duplicate_booking:
            connection.rollback()

            flash(
                "You already have a pending booking for these dates. "
                "Please complete payment or wait for it to expire.",
                "error"
            )

            return redirect(
                url_for(
                    "payment_page",
                    pending_booking_id=duplicate_booking["pending_booking_id"]
                )
            )

        # Recheck availability and select one clean room
        selected_room = connection.execute(
            """
            SELECT r.room_id, r.room_number
            FROM rooms r
            WHERE r.category_id = ?
              AND r.is_active = 1
              AND r.maintenance_status = 'Operational'
              AND r.housekeeping_status = 'Clean/Ready'
              AND NOT EXISTS (
                  SELECT 1
                  FROM reservations res
                  WHERE res.room_id = r.room_id
                    AND res.booking_status IN ('Confirmed', 'Checked-in')
                    AND res.checkin_date < ?
                    AND res.checkout_date > ?
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM maintenance_reports mr
                  WHERE mr.room_id = r.room_id
                    AND mr.maintenance_status IN ('Reported', 'In Progress')
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM room_holds h
                  WHERE h.room_id = r.room_id
                    AND h.checkin_date < ?
                    AND h.checkout_date > ?
                    AND h.hold_expires_at > CURRENT_TIMESTAMP
              )
            ORDER BY r.room_number
            LIMIT 1
            """,
            (
                category_id,
                checkout_date,
                checkin_date,
                checkout_date,
                checkin_date
            )
        ).fetchone()

        if selected_room is None:
            connection.rollback()
            return (
                "Sorry, no clean and ready rooms are available "
                "for these dates. Please try another date.",
                409
            )

        # Retrieve the currently logged-in guest
        guest = connection.execute(
            """
            SELECT guest_id, full_name, email
            FROM guests
            WHERE guest_id = ?
            """,
            (session["guest_id"],)
        ).fetchone()

        if guest is None:
            connection.rollback()
            return "Guest account not found. Please log in again.", 401

        guest_id = guest["guest_id"]
        full_name = guest["full_name"]
        email = guest["email"]

        # Update guest contact and identification details
        connection.execute(
            """
            UPDATE guests
            SET phone = ?, address = ?, id_type = ?, id_number = ?
            WHERE guest_id = ?
            """,
            (
                phone.strip(),
                address.strip(),
                id_type,
                id_number.strip(),
                guest_id
            )
        )

        # Calculate nightly seasonal prices on the server
        base_price = category["base_price"]
        nightly_rates = []
        total_amount = 0

        for day in range((checkout - checkin).days):

            current_date = checkin + timedelta(days=day)

            if current_date.month >= 11 or current_date.month <= 5:
                season_name = "Peak Season"
            else:
                season_name = "Normal Season"

            season = connection.execute(
                """
                SELECT price_multiplier
                FROM seasons
                WHERE season_name = ?
                """,
                (season_name,)
            ).fetchone()

            if season is None:
                raise ValueError("Seasonal pricing information is missing.")

            multiplier = season["price_multiplier"]
            nightly_price = base_price * multiplier
            total_amount += nightly_price

            nightly_rates.append({
                "stay_date": current_date.strftime("%Y-%m-%d"),
                "season_name": season_name,
                "multiplier": multiplier,
                "nightly_price": nightly_price
            })

        # Generate unique booking reference
        booking_reference = "HTL-" + uuid.uuid4().hex[:10].upper()

        # Set the 10-minute payment deadline
        payment_deadline = datetime.now() + timedelta(minutes=10)
        expires_at = payment_deadline.strftime("%Y-%m-%d %H:%M:%S")

        # Store occupants and pricing details as JSON
        booking_data = {
            "guest_name": full_name,
            "guest_email": email,
            "guest_phone": phone,
            "guest_address": address,
            "id_type": id_type,
            "id_number": id_number,
            "occupants": [
                {
                    "occupant_name": name.strip(),
                    "age": int(age)
                }
                for name, age in zip(occupant_names, occupant_ages)
            ],
            "base_price": base_price,
            "nightly_rates": nightly_rates
        }

        booking_data_json = json.dumps(booking_data)

        # Create the pending booking
        pending_cursor = connection.execute(
            """
            INSERT INTO pending_bookings (
                booking_reference,
                guest_id,
                room_id,
                checkin_date,
                checkout_date,
                number_of_guests,
                total_amount,
                booking_data,
                expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                booking_reference,
                guest_id,
                selected_room["room_id"],
                checkin_date,
                checkout_date,
                number_of_guests,
                total_amount,
                booking_data_json,
                expires_at
            )
        )

        pending_booking_id = pending_cursor.lastrowid

        # Temporarily hold the selected room for this guest
        connection.execute(
            """
            INSERT INTO room_holds (
                room_id,
                guest_id,
                checkin_date,
                checkout_date,
                hold_expires_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                selected_room["room_id"],
                guest_id,
                checkin_date,
                checkout_date,
                expires_at
            )
        )

        # Save the pending booking and room hold together
        connection.commit()

        # Display booking details before payment
        return render_template(
            "confirmation.html",
            pending_booking_id=pending_booking_id,
            booking_reference=booking_reference,
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            number_of_nights=(checkout - checkin).days,
            guests=number_of_guests,
            room_number=selected_room["room_number"],
            category_name=category["category_name"],
            guest_name=full_name,
            guest_email=email,
            guest_phone=phone,
            occupants=booking_data["occupants"],
            nightly_rates=nightly_rates,
            total_amount=total_amount,
            payment_deadline=payment_deadline.strftime("%H:%M:%S")
        )

    except Exception as error:

        connection.rollback()
        print("Pending booking error:", error)

        return "Unable to process your booking. Please try again.", 500

    finally:
        connection.close()

@app.route("/expire-pending-booking/<int:pending_booking_id>", methods=["POST"])
def expire_pending_booking(pending_booking_id):

    if "guest_id" not in session:
        return "Unauthorized", 401

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        booking = connection.execute(
            """
            SELECT *
            FROM pending_bookings
            WHERE pending_booking_id = ?
              AND guest_id = ?
            """,
            (pending_booking_id, session["guest_id"])
        ).fetchone()

        if booking is None:
            connection.rollback()
            return "Booking not found", 404

        if booking["status"] != "Pending":
            connection.rollback()
            return "Booking already processed", 409

        expiry_time = datetime.strptime(
            booking["expires_at"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() < expiry_time:
            connection.rollback()
            return "Payment window is still active", 400

        connection.execute(
            """
            UPDATE pending_bookings
            SET status = 'Expired'
            WHERE pending_booking_id = ?
            """,
            (pending_booking_id,)
        )

        connection.execute(
            """
            DELETE FROM room_holds
            WHERE room_id = ?
              AND guest_id = ?
              AND checkin_date = ?
              AND checkout_date = ?
            """,
            (
                booking["room_id"],
                booking["guest_id"],
                booking["checkin_date"],
                booking["checkout_date"]
            )
        )

        connection.commit()
        return "Booking expired and room hold released", 200

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

@app.route("/pending-qr/<int:pending_booking_id>")
def pending_qr(pending_booking_id):

    if "guest_id" not in session:
        return "Unauthorized", 401

    connection = get_db_connection()

    try:
        booking = connection.execute(
            """
            SELECT booking_reference, total_amount
            FROM pending_bookings
            WHERE pending_booking_id = ?
              AND guest_id = ?
              AND expires_at > ?
            """,
            (
                pending_booking_id,
                session["guest_id"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        ).fetchone()

        if booking is None:
            return "Booking not found or payment window expired.", 404

        qr_data = (
            "Breezy Palms - SIMULATED PAYMENT\n"
            f"Booking Reference: {booking['booking_reference']}\n"
            f"Amount: INR {booking['total_amount']:.2f}\n"
            "DEMO ONLY - NO REAL PAYMENT"
        )

        qr_image = qrcode.make(qr_data)

        image_buffer = BytesIO()
        qr_image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        return send_file(
            image_buffer,
            mimetype="image/png"
        )

    finally:
        connection.close()
        

@app.route("/process-payment/<int:pending_booking_id>", methods=["POST"])
def process_payment(pending_booking_id):

    if "guest_id" not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for("guest_login"))

    payment_result = request.form.get("payment_result")

    if payment_result not in ["Successful", "Failed"]:
        flash("Invalid payment selection.", "error")
        return redirect(url_for(
            "payment_page",
            pending_booking_id=pending_booking_id
        ))

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        booking = connection.execute(
            """
            SELECT *
            FROM pending_bookings
            WHERE pending_booking_id = ?
              AND guest_id = ?
            """,
            (pending_booking_id, session["guest_id"])
        ).fetchone()

        if booking is None:
            connection.rollback()
            flash("Booking not found.", "error")
            return redirect("/")

        if booking["status"] != "Pending":
            connection.rollback()
            flash("This booking has already been processed.", "error")
            return redirect("/")

        expiry_time = datetime.strptime(
            booking["expires_at"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() >= expiry_time:

            connection.execute(
                """
                UPDATE pending_bookings
                SET status = 'Expired'
                WHERE pending_booking_id = ?
                """,
                (pending_booking_id,)
            )

            connection.execute(
                """
                DELETE FROM room_holds
                WHERE room_id = ?
                  AND guest_id = ?
                  AND checkin_date = ?
                  AND checkout_date = ?
                """,
                (
                    booking["room_id"],
                    booking["guest_id"],
                    booking["checkin_date"],
                    booking["checkout_date"]
                )
            )

            connection.commit()

            flash("Payment time expired. Please book again.", "error")
            return redirect("/")

        payment_reference = "PAY-" + uuid.uuid4().hex[:12].upper()

        connection.execute(
            """
            INSERT INTO payment_attempts (
                pending_booking_id,
                payment_reference,
                payment_method,
                payment_amount,
                payment_status
            )
            VALUES (?, ?, 'UPI', ?, ?)
            """,
            (
                pending_booking_id,
                payment_reference,
                booking["total_amount"],
                payment_result
            )
        )

        if payment_result == "Failed":

            connection.execute(
                """
                UPDATE pending_bookings
                SET status = 'Failed'
                WHERE pending_booking_id = ?
                """,
                (pending_booking_id,)
            )

            connection.execute(
                """
                DELETE FROM room_holds
                WHERE room_id = ?
                  AND guest_id = ?
                  AND checkin_date = ?
                  AND checkout_date = ?
                """,
                (
                    booking["room_id"],
                    booking["guest_id"],
                    booking["checkin_date"],
                    booking["checkout_date"]
                )
            )

            connection.commit()

            return render_template(
                "payment_failed.html",
                 booking_reference=booking["booking_reference"]
            )

        booking_data = json.loads(booking["booking_data"])

        cursor = connection.execute(
            """
            INSERT INTO reservations (
                booking_reference,
                guest_id,
                room_id,
                checkin_date,
                checkout_date,
                number_of_guests,
                booking_status,
                total_amount,
                payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Confirmed', ?, 'Successful')
            """,
            (
                booking["booking_reference"],
                booking["guest_id"],
                booking["room_id"],
                booking["checkin_date"],
                booking["checkout_date"],
                booking["number_of_guests"],
                booking["total_amount"]
            )
        )

        reservation_id = cursor.lastrowid

        for occupant in booking_data["occupants"]:
            connection.execute(
                """
                INSERT INTO reservation_occupants (
                    reservation_id,
                    occupant_name,
                    age
                )
                VALUES (?, ?, ?)
                """,
                (
                    reservation_id,
                    occupant["occupant_name"],
                    occupant["age"]
                )
            )

        for rate in booking_data["nightly_rates"]:

            base_price = booking_data["base_price"]
            nightly_price = rate["nightly_price"]

            season_multiplier = rate.get("season_multiplier")

            if season_multiplier is None:
                season_multiplier = nightly_price / base_price

            connection.execute(
        """
        INSERT INTO reservation_nightly_rates (
            reservation_id,
            stay_date,
            base_price,
            season_multiplier,
            nightly_price
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reservation_id,
            rate["stay_date"],
            base_price,
            season_multiplier,
            nightly_price
        )
    )

        connection.execute(
            """
            INSERT INTO payments (
                reservation_id,
                payment_reference,
                payment_method,
                payment_amount,
                payment_status
            )
            VALUES (?, ?, 'UPI', ?, 'Successful')
            """,
            (
                reservation_id,
                payment_reference,
                booking["total_amount"]
            )
        )

        connection.execute(
            """
            UPDATE pending_bookings
            SET status = 'Completed'
            WHERE pending_booking_id = ?
            """,
            (pending_booking_id,)
        )

        connection.execute(
            """
            DELETE FROM room_holds
            WHERE room_id = ?
              AND guest_id = ?
              AND checkin_date = ?
              AND checkout_date = ?
            """,
            (
                booking["room_id"],
                booking["guest_id"],
                booking["checkin_date"],
                booking["checkout_date"]
            )
        )

        connection.commit()

        return redirect(url_for(
            "payment_success",
            reservation_id=reservation_id
        ))

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

@app.route("/payment-success/<int:reservation_id>")
def payment_success(reservation_id):

    if "guest_id" not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for("guest_login"))

    connection = get_db_connection()

    try:
        reservation = connection.execute(
            """
            SELECT
                r.reservation_id,
                r.booking_reference,
                r.checkin_date,
                r.checkout_date,
                r.number_of_guests,
                r.total_amount,
                r.booking_status,
                r.payment_status,
                rm.room_number,
                rc.category_name,
                g.full_name
            FROM reservations r
            JOIN rooms rm ON r.room_id = rm.room_id
            JOIN room_categories rc ON rm.category_id = rc.category_id
            JOIN guests g ON r.guest_id = g.guest_id
            WHERE r.reservation_id = ?
              AND r.guest_id = ?
            """,
            (reservation_id, session["guest_id"])
        ).fetchone()

        if reservation is None:
            flash("Reservation not found.", "error")
            return redirect(url_for("my_bookings"))

        return render_template(
            "payment_success.html",
            reservation=reservation,
            guest_name=session.get("guest_name")
        )

    finally:
        connection.close()

# ----------------------------------------
# Generate Pending Booking Bill (PDF)
# ----------------------------------------

@app.route("/payment/<int:pending_booking_id>")
def payment_page(pending_booking_id):

    if "guest_id" not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for("guest_login"))

    connection = get_db_connection()

    try:
        pending_booking = connection.execute(
            """
            SELECT
                pb.pending_booking_id,
                pb.booking_reference,
                pb.guest_id,
                pb.total_amount,
                pb.expires_at,
                rm.room_number,
                rc.category_name
            FROM pending_bookings pb
            JOIN rooms rm ON pb.room_id = rm.room_id
            JOIN room_categories rc ON rm.category_id = rc.category_id
            WHERE pb.pending_booking_id = ?
              AND pb.guest_id = ?
            """,
            (pending_booking_id, session["guest_id"])
        ).fetchone()

        if pending_booking is None:
            flash("Booking not found. Please try booking again.", "error")
            return redirect(url_for("home"))

        expiry_time = datetime.strptime(
            pending_booking["expires_at"],
            "%Y-%m-%d %H:%M:%S"
        )

        if datetime.now() >= expiry_time:
            connection.execute(
                "DELETE FROM room_holds WHERE guest_id = ?",
                (session["guest_id"],)
            )
            connection.execute(
                "DELETE FROM pending_bookings WHERE pending_booking_id = ?",
                (pending_booking_id,)
            )
            connection.commit()

            flash("Your payment time has expired. Please book again.", "error")
            return redirect(url_for("home"))

        return render_template(
            "payment.html",
            booking=pending_booking,
            guest_name=session.get("guest_name")
        )

    finally:
        connection.close()

@app.route("/generate-bill/<int:pending_booking_id>")
def generate_pending_bill(pending_booking_id):

    # Check guest login
    if "guest_id" not in session:
        flash("Please log in to access your bill.", "error")
        return redirect(url_for("guest_login"))

    connection = get_db_connection()

    try:
        # Retrieve pending booking
        booking = connection.execute(
            """
            SELECT
                pb.*,
                g.full_name,
                g.email,
                g.phone,
                rm.room_number,
                rc.category_name
            FROM pending_bookings pb
            JOIN guests g ON pb.guest_id = g.guest_id
            JOIN rooms rm ON pb.room_id = rm.room_id
            JOIN room_categories rc ON rm.category_id = rc.category_id
            WHERE pb.pending_booking_id = ?
              AND pb.guest_id = ?
            """,
            (pending_booking_id, session["guest_id"])
        ).fetchone()

        if booking is None:
            return "Booking not found or access denied.", 404

        # Retrieve stored booking information
        booking_data = json.loads(booking["booking_data"])

        # Create PDF in memory
        pdf_buffer = BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=A4)

        width, height = A4
        y = height - 55

        # Breezy Palms Hotel Heading
        breezy_width = pdfmetrics.stringWidth(
            "Breezy", "Poppins-Bold", 30
        )
        palms_width = pdfmetrics.stringWidth(
            "Palms", "DancingScript", 28
        )

        gap = 8
        total_width = breezy_width + gap + palms_width
        start_x = (width - total_width) / 2

        pdf.setFont("Poppins-Bold", 30)
        pdf.setFillColorRGB(1.0, 0.788, 0.157)
        pdf.drawString(start_x, y, "Breezy")

        pdf.setFont("DancingScript", 28)
        pdf.setFillColorRGB(0.224, 1.0, 0.078)
        pdf.drawString(
            start_x + breezy_width + gap, y, "Palms"
        )

        pdf.setFillColorRGB(0, 0, 0)
        y -= 35

        # Bill heading
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(width / 2, y, "BOOKING BILL")
        y -= 35

        # Payment status
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "PAYMENT STATUS: PENDING")
        y -= 30

        # Booking details
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Booking Details")
        y -= 22

        pdf.setFont("Helvetica", 10)

        details = [
            f"Booking Reference: {booking['booking_reference']}",
            f"Guest Name: {booking['full_name']}",
            f"Email: {booking['email']}",
            f"Phone: {booking_data.get('guest_phone', '')}",
            f"Room Number: {booking['room_number']}",
            f"Room Category: {booking['category_name']}",
            f"Check-in: {booking['checkin_date']}",
            f"Check-out: {booking['checkout_date']}",
            f"Number of Guests: {booking['number_of_guests']}"
        ]

        for detail in details:
            pdf.drawString(50, y, detail)
            y -= 18

        # Occupant details
        y -= 10
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Occupant Details")
        y -= 22

        pdf.setFont("Helvetica", 10)

        for index, occupant in enumerate(
            booking_data.get("occupants", []), start=1
        ):
            pdf.drawString(
                50,
                y,
                f"Guest {index}: {occupant['occupant_name']} "
                f"(Age: {occupant['age']})"
            )
            y -= 18

        # Nightly pricing
        y -= 10
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Nightly Rate Breakdown")
        y -= 22

        pdf.setFont("Helvetica", 10)

        for rate in booking_data.get("nightly_rates", []):
            pdf.drawString(50, y, rate["stay_date"])

            pdf.drawRightString(
                width - 50,
                y,
                f"Rs. {rate['nightly_price']:.2f}"
            )

            y -= 18

        # Total amount
        y -= 15
        pdf.line(50, y, width - 50, y)
        y -= 25

        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(50, y, "TOTAL BOOKING AMOUNT")

        pdf.drawRightString(
            width - 50,
            y,
            f"Rs. {booking['total_amount']:.2f}"
        )

        y -= 35

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Payment is pending.")
        y -= 18

        pdf.setFont("Helvetica", 9)
        pdf.drawString(
            50,
            y,
            "This is a provisional bill and not a payment receipt."
        )

        # Cancellation and Refund Policy
        y -= 40

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "CANCELLATION AND REFUND POLICY")
        y -= 22

        pdf.setFont("Helvetica", 9)

        policy_lines = [
            "Up to 72 hours or more before check-in: 100% refund",
            "Up to 48 hours before check-in: 50% refund",
            "Up to 24 hours before check-in: No refund"
        ]

        for line in policy_lines:
            pdf.drawString(55, y, "- " + line)
            y -= 16

        y -= 8

        # Refund statement
        pdf.setFont("Helvetica-Oblique", 8)
        pdf.drawString(
    50,
    y,
    "Refunds are simulated and recorded by the hotel system."
        )

# Move down for the tax statement
        y -= 15

        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(
    50,
    y,
    "Taxes as applicable will be EXTRA."
        )

        # Save PDF
        pdf.save()
        pdf_buffer.seek(0)

        # Open in browser by default; download when requested
        download = request.args.get("download") == "1"

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=download,
            download_name=f"Bill_{booking['booking_reference']}.pdf"
        )

    finally:
        connection.close()

# ----------------------------------------
# 7. Administrator Dashboard
# ----------------------------------------

@app.route("/admin-dashboard")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") != "Administrator":
        return "Access denied. Administrator privileges required.", 403

    connection = get_db_connection()

    try:

        # Total reservations
        total_reservations = connection.execute(
            """
            SELECT COUNT(*)
            FROM reservations
            """
        ).fetchone()[0]

        # Total registered guest accounts
        registered_guests = connection.execute(
            """
            SELECT COUNT(*)
            FROM guests
            """
        ).fetchone()[0]

        # Guests who have at least one non-cancelled reservation
        guests_with_bookings = connection.execute(
            """
            SELECT COUNT(DISTINCT guest_id)
            FROM reservations
            WHERE booking_status != 'Cancelled'
            """
        ).fetchone()[0]

        # Registered guests who have no non-cancelled reservations
        guests_without_bookings = (
            registered_guests - guests_with_bookings
        )

        # Total guests across reservations
        total_guests = connection.execute(
            """
            SELECT COUNT(*)
            FROM reservation_occupants ro
            JOIN reservations r
                ON ro.reservation_id = r.reservation_id
            WHERE r.booking_status != 'Cancelled'
            """
        ).fetchone()[0]

        # Total active rooms
        total_rooms = connection.execute(
            """
            SELECT COUNT(*)
            FROM rooms
            WHERE is_active = 1
            """
        ).fetchone()[0]

        # Currently occupied rooms
        occupied_rooms = connection.execute(
            """
            SELECT COUNT(DISTINCT room_id)
            FROM reservations
            WHERE booking_status = 'Checked-in'
            """
        ).fetchone()[0]

        # Room category overview
        category_stats = connection.execute(
            """
            SELECT
                rc.category_name,

                COUNT(DISTINCT CASE
                    WHEN rooms.is_active = 1
                    THEN rooms.room_id
                END) AS total_rooms,

                COUNT(DISTINCT CASE
                    WHEN rooms.is_active = 1
                    AND EXISTS (
                        SELECT 1
                        FROM reservations r
                        WHERE r.room_id = rooms.room_id
                          AND r.booking_status IN (
                              'Confirmed', 'Checked-in'
                          )
                    )
                    THEN rooms.room_id
                END) AS booked_rooms

            FROM room_categories rc
            LEFT JOIN rooms
                ON rc.category_id = rooms.category_id
            GROUP BY rc.category_id
            ORDER BY rc.category_id
            """
        ).fetchall()

        category_stats = [
            {
                "category_name": row["category_name"],
                "total_rooms": row["total_rooms"],
                "booked_rooms": row["booked_rooms"],
                "available_rooms": row["total_rooms"] - row["booked_rooms"]
            }
            for row in category_stats
        ]

        # Recent reservations
        recent_reservations = connection.execute(
            """
            SELECT
                r.booking_reference,
                g.full_name AS guest_name,
                rm.room_number,
                r.checkin_date,
                r.checkout_date,
                r.booking_status
            FROM reservations r
            JOIN guests g
                ON r.guest_id = g.guest_id
            JOIN rooms rm
                ON r.room_id = rm.room_id
            ORDER BY r.created_at DESC
            LIMIT 10
            """
        ).fetchall()

        return render_template(
            "admin_dashboard.html",
            total_reservations=total_reservations,
            total_guests=total_guests,
            registered_guests=registered_guests,
            guests_with_bookings=guests_with_bookings,
            guests_without_bookings=guests_without_bookings,
            total_rooms=total_rooms,
            occupied_rooms=occupied_rooms,
            category_stats=category_stats,
            recent_reservations=recent_reservations
        )

    finally:
        connection.close()

# ----------------------------------------
# Guest Management
# ----------------------------------------  

@app.route("/guest-management")
def guest_management():

    # Check whether the user is logged in
    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    # Only administrators and receptionists can access Guest Management
    if session.get("role") not in ["Administrator", "Receptionist"]:
        return "Access Denied", 403
    
    connection = get_db_connection()

    try:
        guests = connection.execute(
            """
            SELECT
                g.guest_id,
                g.full_name,
                g.email,
                g.phone,
                COUNT(
                    DISTINCT CASE
                        WHEN r.booking_status != 'Cancelled'
                        THEN r.reservation_id
                    END
                ) AS total_bookings
            FROM guests g
            LEFT JOIN reservations r
                ON g.guest_id = r.guest_id
            GROUP BY
                g.guest_id,
                g.full_name,
                g.email,
                g.phone
            ORDER BY g.guest_id DESC
            """
        ).fetchall()

        return render_template(
            "guest_management.html",
            guests=guests
        )

    finally:
        connection.close()

# ----------------------------------------
# Guest Booking History
# ----------------------------------------

@app.route("/guest-bookings/<int:guest_id>")
def guest_bookings(guest_id):

    # Check whether the user is logged in
    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    # Allow only administrators and receptionists
    if session.get("role") not in ["Administrator", "Receptionist"]:
        return "Access Denied", 403

    connection = get_db_connection()

    try:
        # Retrieve guest details
        guest = connection.execute(
            """
            SELECT guest_id, full_name, email, phone
            FROM guests
            WHERE guest_id = ?
            """,
            (guest_id,)
        ).fetchone()

        if guest is None:
            return "Guest not found.", 404

        # Retrieve all reservations belonging to this guest
        bookings = connection.execute(
            """
            SELECT
                r.booking_reference,
                r.checkin_date,
                r.checkout_date,
                r.number_of_guests,
                (
                    SELECT GROUP_CONCAT(ro.occupant_name, '|')
                    FROM reservation_occupants ro
                    WHERE ro.reservation_id = r.reservation_id
                ) AS occupant_names,
                r.total_amount,
                r.booking_status,
                rm.room_number,
                rc.category_name
            FROM reservations r
            JOIN rooms rm
                ON r.room_id = rm.room_id
            JOIN room_categories rc
                ON rm.category_id = rc.category_id
            WHERE r.guest_id = ?
            ORDER BY r.created_at DESC
            """,
            (guest_id,)
        ).fetchall()

        return render_template(
            "guest_management.html",
             guests=None,
             selected_guest=guest,
             bookings=bookings
        )

    finally:
        connection.close()

# ----------------------------------------
# 8. RECEPTIONIST DASHBOARD AND STAFF LOGOUT 
# ----------------------------------------    
@app.route("/receptionist-dashboard")
def receptionist_dashboard():

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") not in ["Administrator", "Receptionist"]:
        return "Access denied. Administrator or Receptionist privileges required.", 403

    connection = get_db_connection()

    try:
        today = datetime.now().date().isoformat()

        total_reservations = connection.execute(
            """
            SELECT COUNT(*)
            FROM reservations
            """
        ).fetchone()[0]

        total_guests = connection.execute(
            """
            SELECT COUNT(*)
            FROM reservation_occupants ro
            JOIN reservations r
                ON ro.reservation_id = r.reservation_id
            WHERE r.booking_status != 'Cancelled'
            """
        ).fetchone()[0]

        occupied_rooms = connection.execute(
            """
            SELECT COUNT(*)
            FROM reservations
            WHERE booking_status = 'Checked-in'
            """
        ).fetchone()[0]

        available_rooms = connection.execute(
            """
            SELECT COUNT(*)
            FROM rooms rm
            WHERE rm.is_active = 1
              AND rm.housekeeping_status = 'Clean/Ready'
              AND rm.maintenance_status = 'Operational'
              AND NOT EXISTS (
                  SELECT 1
                  FROM reservations r
                  WHERE r.room_id = rm.room_id
                    AND r.booking_status IN ('Confirmed', 'Checked-in')
                    AND r.checkin_date <= ?
                    AND r.checkout_date > ?
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM maintenance_reports mr
                  WHERE mr.room_id = rm.room_id
                    AND mr.maintenance_status != 'Resolved'
              )
            """,
            (today, today)
        ).fetchone()[0]

        recent_reservations = connection.execute(
            """
            SELECT
                r.reservation_id,
                r.booking_reference,
                g.full_name AS guest_name,
                rm.room_number,
                r.checkin_date,
                r.checkout_date,
                r.booking_status
            FROM reservations r
            JOIN guests g
                ON r.guest_id = g.guest_id
            JOIN rooms rm
                ON r.room_id = rm.room_id
            ORDER BY r.created_at DESC
            LIMIT 10
            """
        ).fetchall()

    finally:
        connection.close()

    return render_template(
        "receptionist_dashboard.html",
        total_reservations=total_reservations,
        total_guests=total_guests,
        available_rooms=available_rooms,
        occupied_rooms=occupied_rooms,
        recent_reservations=recent_reservations,
    )

# ----------------------------------------
# 9. HOUSEKEEPING DASHBOARD
# ----------------------------------------

@app.route("/housekeeping-dashboard")
def housekeeping_dashboard():

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") not in ["Administrator", "Receptionist", "Housekeeping Staff"]:
        return "Access denied. You do not have permission to access this dashboard.", 403

    connection = get_db_connection()

    try:
        rooms = connection.execute(
            """
            SELECT
                room_id,
                room_number,
                housekeeping_status,
                maintenance_status
            FROM rooms
            WHERE is_active = 1
            ORDER BY CAST(room_number AS INTEGER)
            """
        ).fetchall()

        total_rooms = len(rooms)

        dirty_rooms = sum(
            1 for room in rooms
            if room["housekeeping_status"] == "Dirty/Vacant"
        )

        cleaning_rooms = sum(
            1 for room in rooms
            if room["housekeeping_status"] == "Cleaning In Progress"
        )

        clean_rooms = sum(
            1 for room in rooms
            if room["housekeeping_status"] == "Clean/Ready"
        )

    finally:
        connection.close()

    return render_template(
        "housekeeping_dashboard.html",
        rooms=rooms,
        total_rooms=total_rooms,
        dirty_rooms=dirty_rooms,
        cleaning_rooms=cleaning_rooms,
        clean_rooms=clean_rooms
    )

# START ROOM CLEANING AND CREATE ASSIGNMENT

@app.route("/start-cleaning/<int:room_id>", methods=["POST"])
def start_cleaning(room_id):

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") != "Housekeeping Staff":
        return "Access denied. Housekeeping Staff privileges required.", 403

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Cleaning In Progress'
            WHERE room_id = ?
              AND is_active = 1
              AND housekeeping_status = 'Dirty/Vacant'
              AND maintenance_status = 'Operational'
            """,
            (room_id,)
        )

        if cursor.rowcount == 1:
            connection.execute(
                """
                INSERT INTO housekeeping_assignments (
                    room_id,
                    assigned_to,
                    assigned_date,
                    started_at,
                    cleaning_status
                )
                VALUES (?, ?, DATE('now'), CURRENT_TIMESTAMP,
                        'Cleaning In Progress')
                """,
                (room_id, session["user_id"])
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("housekeeping_dashboard"))


# ----------------------------------------
# MAINTENANCE MANAGEMENT DASHBOARD
# ----------------------------------------

@app.route("/maintenance-dashboard")
def maintenance_dashboard():

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") not in ["Administrator", "Receptionist"]:
        return "Access denied. Administrator or Receptionist privileges required.", 403

    connection = get_db_connection()

    total_reports = connection.execute(
        "SELECT COUNT(*) AS total FROM maintenance_reports"
    ).fetchone()["total"]

    reported_count = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM maintenance_reports
        WHERE maintenance_status = 'Reported'
        """
    ).fetchone()["total"]

    in_progress_count = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM maintenance_reports
        WHERE maintenance_status = 'In Progress'
        """
    ).fetchone()["total"]

    resolved_count = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM maintenance_reports
        WHERE maintenance_status = 'Resolved'
        """
    ).fetchone()["total"]

    maintenance_reports = connection.execute(
        """
        SELECT
            mr.report_id,
            rm.room_number,
            mr.issue_description,
            u.full_name AS reported_by_name,
            mr.reported_at,
            mr.maintenance_status
        FROM maintenance_reports mr
        JOIN rooms rm ON mr.room_id = rm.room_id
        JOIN users u ON mr.reported_by = u.user_id
        ORDER BY mr.reported_at DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "maintenance_dashboard.html",
        total_reports=total_reports,
        reported_count=reported_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        maintenance_reports=maintenance_reports
    )

# COMPLETE ROOM CLEANING AND UPDATE ASSIGNMENT


@app.route("/complete-cleaning/<int:room_id>", methods=["POST"])
def complete_cleaning(room_id):

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") != "Housekeeping Staff":
        return "Access denied. Housekeeping Staff privileges required.", 403

    connection = get_db_connection()

    try:
        # Check whether the room has an active housekeeping assignment
        assignment = connection.execute(
            """
            SELECT assignment_id
            FROM housekeeping_assignments
            WHERE room_id = ?
              AND cleaning_status = 'Cleaning In Progress'
            ORDER BY assignment_id DESC
            LIMIT 1
            """,
            (room_id,)
        ).fetchone()

        # Do not complete cleaning without an active assignment
        if assignment is None:
            connection.rollback()
            return redirect(url_for("housekeeping_dashboard"))

        # Complete cleaning only if the room is operational
        cursor = connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Clean/Ready'
            WHERE room_id = ?
              AND is_active = 1
              AND housekeeping_status = 'Cleaning In Progress'
              AND maintenance_status = 'Operational'
            """,
            (room_id,)
        )

        if cursor.rowcount == 1:

            # Mark the active housekeeping assignment as completed
            connection.execute(
                """
                UPDATE housekeeping_assignments
                SET cleaning_status = 'Completed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE assignment_id = ?
                """,
                (assignment["assignment_id"],)
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("housekeeping_dashboard"))

# REPORT ROOM MAINTENANCE ISSUE

@app.route("/report-maintenance", methods=["POST"])
def report_maintenance():

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") != "Housekeeping Staff":
        return "Access denied. Housekeeping Staff privileges required.", 403

    room_id = request.form.get("room_id")
    issue_description = request.form.get("issue_description", "").strip()

    if not room_id or not issue_description:
        return "Please select a room and describe the issue.", 400

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        room = connection.execute(
            """
            SELECT room_id, maintenance_status
            FROM rooms
            WHERE room_id = ? AND is_active = 1
            """,
            (room_id,)
        ).fetchone()

        if room is None:
            connection.rollback()
            return "Invalid room selected.", 400

        if room["maintenance_status"] == "Under Maintenance":
            connection.rollback()
            return "This room is already under maintenance.", 409

        connection.execute(
            """
            INSERT INTO maintenance_reports (
                room_id,
                reported_by,
                issue_description,
                reported_at,
                maintenance_status
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'Reported')
            """,
            (room_id, session["user_id"], issue_description)
        )

        connection.execute(
            """
            UPDATE rooms
            SET maintenance_status = 'Under Maintenance'
            WHERE room_id = ?
            """,
            (room_id,)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("housekeeping_dashboard"))

# STAFF LOGOUT

@app.route("/staff-logout")
def staff_logout():
    session.clear()
    return redirect(url_for("staff_login"))

# ----------------------------------------
# CHECK IN GUEST
# ----------------------------------------

@app.route("/check-in/<int:reservation_id>", methods=["POST"])
def checkin_guest(reservation_id):

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") not in ["Administrator", "Receptionist"]:
        return "Access denied. Administrator or Receptionist privileges required.", 403

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        reservation = connection.execute(
            """
            SELECT r.room_id, r.booking_status, r.checkin_date, r.checkout_date,
                   rm.housekeeping_status, rm.maintenance_status, rm.is_active
            FROM reservations r
            JOIN rooms rm ON r.room_id = rm.room_id
            WHERE r.reservation_id = ?
            """,
            (reservation_id,)
        ).fetchone()

        if reservation is None:
            connection.rollback()
            return "Reservation not found.", 404

        if reservation["booking_status"] != "Confirmed":
            connection.rollback()
            return "Only confirmed reservations can be checked in.", 400

        today = datetime.now().date()
        checkin_date = datetime.strptime(
            reservation["checkin_date"], "%Y-%m-%d"
        ).date()
        checkout_date = datetime.strptime(
            reservation["checkout_date"], "%Y-%m-%d"
        ).date()

        if not checkin_date <= today < checkout_date:
            connection.rollback()
            return "Check-in is allowed only during the reservation dates.", 400

        if reservation["is_active"] != 1:
            connection.rollback()
            return "This room is inactive.", 400

        if reservation["housekeeping_status"] != "Clean/Ready":
            connection.rollback()
            return "The room is not clean and ready for check-in.", 400

        if reservation["maintenance_status"] != "Operational":
            connection.rollback()
            return "The room is under maintenance and cannot be checked in.", 400

        unresolved_report = connection.execute(
            """
            SELECT report_id
            FROM maintenance_reports
            WHERE room_id = ?
              AND maintenance_status != 'Resolved'
            LIMIT 1
            """,
            (reservation["room_id"],)
        ).fetchone()

        if unresolved_report:
            connection.rollback()
            return "The room has an unresolved maintenance report.", 400

        connection.execute(
            """
            UPDATE reservations
            SET booking_status = 'Checked-in'
            WHERE reservation_id = ?
              AND booking_status = 'Confirmed'
            """,
            (reservation_id,)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("receptionist_dashboard"))

# ----------------------------------------
# CHECK OUT GUEST AND UPDATE ROOM STATUS
# ----------------------------------------

@app.route("/checkout/<int:reservation_id>", methods=["POST"])
def checkout_guest(reservation_id):

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") not in ["Administrator", "Receptionist"]:
        return "Access denied. Administrator or Receptionist privileges required.", 403

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        reservation = connection.execute(
            """
            SELECT room_id, booking_status
            FROM reservations
            WHERE reservation_id = ?
            """,
            (reservation_id,)
        ).fetchone()

        if reservation is None:
            connection.rollback()
            return "Reservation not found.", 404

        if reservation["booking_status"] != "Checked-in":
            connection.rollback()
            return "Only checked-in reservations can be checked out.", 400

        connection.execute(
            """
            UPDATE reservations
            SET booking_status = 'Checked-out'
            WHERE reservation_id = ?
            """,
            (reservation_id,)
        )

        connection.execute(
            """
            UPDATE rooms
            SET housekeeping_status = 'Dirty/Vacant'
            WHERE room_id = ?
            """,
            (reservation["room_id"],)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("receptionist_dashboard"))


# ----------------------------------------
# UPDATE MAINTENANCE REPORT STATUS
# ----------------------------------------

@app.route("/update-maintenance-status/<int:report_id>", methods=["POST"])
def update_maintenance_status(report_id):

    if "user_id" not in session:
        return redirect(url_for("staff_login"))

    if session.get("role") not in ["Administrator", "Receptionist"]:
        return "Access denied. Administrator or Receptionist privileges required.", 403

    new_status = request.form.get("maintenance_status")

    if new_status not in ["In Progress", "Resolved"]:
        return "Invalid maintenance status.", 400

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        report = connection.execute(
            """
            SELECT room_id, maintenance_status
            FROM maintenance_reports
            WHERE report_id = ?
            """,
            (report_id,)
        ).fetchone()

        if report is None:
            connection.rollback()
            return "Maintenance report not found.", 404

        current_status = report["maintenance_status"]

        if (
            (current_status == "Reported" and new_status != "In Progress")
            or
            (current_status == "In Progress" and new_status != "Resolved")
        ):
            connection.rollback()
            return "Invalid maintenance status transition.", 400

        if current_status == "Resolved":
            connection.rollback()
            return "This maintenance report is already resolved.", 400

        connection.execute(
            """
            UPDATE maintenance_reports
            SET maintenance_status = ?,
                resolved_at = CASE
                    WHEN ? = 'Resolved' THEN CURRENT_TIMESTAMP
                    ELSE resolved_at
                END
            WHERE report_id = ?
            """,
            (new_status, new_status, report_id)
        )

        # Check whether any unresolved maintenance reports remain for this room.

        unresolved_report = connection.execute(
            """
            SELECT report_id
            FROM maintenance_reports
            WHERE room_id = ?
              AND maintenance_status != 'Resolved'
            LIMIT 1
            """,
            (report["room_id"],)
        ).fetchone()

        if unresolved_report is None:

            connection.execute(
                """
                UPDATE rooms
                SET maintenance_status = 'Operational'
                WHERE room_id = ?
                """,
                (report["room_id"],)
            )

        else:

            connection.execute(
                """
                UPDATE rooms
                SET maintenance_status = 'Under Maintenance'
                WHERE room_id = ?
                """,
                (report["room_id"],)
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return redirect(url_for("maintenance_dashboard"))

# ----------------------------------------
# 9. Run the Application
# ----------------------------------------

if __name__ == "__main__":
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=expire_pending_bookings,
        trigger="interval",
        seconds=30,
        id="pending_booking_expiry",
        max_instances=1,
        coalesce=True
    )

    scheduler.start()

    try:
        app.run(debug=True, use_reloader=False)
    finally:
        scheduler.shutdown()
