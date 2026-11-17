from database.db import get_db_connection

connection = get_db_connection()

query = """
SELECT
    p.pending_booking_id,
    p.booking_reference,
    p.status,
    p.checkin_date,
    p.checkout_date,
    p.expires_at,
    r.room_number,
    rc.category_name
FROM pending_bookings p
JOIN rooms r ON p.room_id = r.room_id
JOIN room_categories rc ON r.category_id = rc.category_id
WHERE p.status = 'Pending'
ORDER BY p.pending_booking_id DESC
"""

rows = connection.execute(query).fetchall()

for row in rows:
    print(dict(row))

connection.close()