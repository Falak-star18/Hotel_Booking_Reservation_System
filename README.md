# 🏨 Hotel Booking and Reservation Management System

A web-based **Hotel Booking and Reservation Management System** developed using Python, Flask, and SQLite. The project is designed to simplify hotel operations by managing room reservations, guest information, billing, housekeeping, maintenance, and staff access through a centralized system.

The system is developed for a single hotel in Goa and provides separate functionalities for guests, administrators, receptionists, and housekeeping staff.

---

## 📌 Purpose

The main purpose of this project is to develop a reliable and user-friendly hotel management system that reduces manual work and makes hotel operations easier to manage.

The system allows guests to explore rooms, check availability, and make reservations, while hotel staff can manage bookings, room conditions, billing, housekeeping activities, and maintenance requests.

The major objectives are:

- Simplify the hotel room booking and reservation process.
- Maintain guest and reservation information in a centralized database.
- Check room availability based on check-in and check-out dates.
- Manage different room categories, prices, and guest capacities.
- Generate billing receipts in PDF format after reservations.
- Provide role-based access for hotel staff.
- Track housekeeping activities and room cleanliness.
- Record maintenance issues and prevent rooms under maintenance from being booked.
- Maintain reliable data through SQLite database integration.

---

## 🏗️ Design Overview

The Hotel Booking and Reservation Management System follows a **modular architecture** in which different functionalities are organized into separate logical components.

The application is developed using the **Agile Software Development Life Cycle (SDLC) model**. The system is developed and tested incrementally, allowing individual modules to be implemented, verified, and improved.

### Design Principles

| Principle | Description |
|---|---|
| **Modularity** | The application is divided into separate functional modules such as booking, billing, housekeeping, and maintenance. |
| **Encapsulation** | Each module handles its own specific operations and related data. |
| **Reusability** | Common functions and database operations can be reused across different parts of the application. |
| **Maintainability** | The modular structure makes it easier to identify, modify, and maintain individual functionalities. |
| **Scalability** | Additional hotel management features can be incorporated in the future. |
| **Testability** | Individual modules and integrated workflows are verified using automated pytest test cases. |
| **Access Control** | Role-based permissions restrict users to the operations allowed for their respective roles. |

### System Architecture

The application follows a three-layer logical architecture:

1. **Presentation Layer**
   - Provides the web interface using HTML and CSS.
   - Allows guests and staff to interact with the system.
   - Displays room information, booking details, dashboards, and other relevant information.

2. **Application Layer**
   - Developed using Python and Flask.
   - Handles booking operations, authentication, billing, housekeeping, maintenance, and business logic.
   - Processes user requests and communicates with the database.

3. **Database Layer**
   - Uses SQLite for persistent data storage.
   - Stores information related to users, guests, rooms, reservations, room categories, housekeeping, and maintenance.

### Data Flow and Module Interaction

The general flow of the system is as follows:

1. **Guest Registration and Authentication**
   - Guests register and log in to access reservation functionality.
   - Staff members log in through the staff login system.

2. **Room Management**
   - Room categories, room details, prices, and capacities are maintained in the database.
   - Room availability is checked using the selected dates and room requirements.

3. **Reservation Management**
   - Guests submit their booking details.
   - The system validates the reservation information and checks room availability.
   - Valid reservations are stored in the database.

4. **Payment and Billing**
   - The reservation is connected to the payment workflow.
   - Billing information is generated for the reservation.
   - A PDF billing receipt is generated with the relevant booking and guest details.

5. **Housekeeping Management**
   - Housekeeping staff view their assigned rooms.
   - Room cleaning statuses are updated.
   - Clean and ready rooms can become available for front desk check-in.

6. **Maintenance Management**
   - Maintenance issues are reported and tracked.
   - Rooms requiring repairs are marked under maintenance.
   - Once the issue is resolved, the room can return to operational status.

7. **Testing and Validation**
   - Individual modules are tested using pytest.
   - Integration tests verify that multiple modules work together correctly.

---

## ✨ Features of the System

### 1. Guest Registration and Login

- Allows new guests to register with their details.
- Provides secure guest authentication.
- Restricts reservation creation to authenticated guests.
- Stores guest information in the database.

### 2. Room Management

The hotel provides four different room categories with different prices and guest capacities.

| Room Category | Base Price per Night | Guest Capacity |
|---|---:|---:|
| Standard Room | ₹3,000 | 1–2 |
| Deluxe Room | ₹4,000 | 1–4 |
| Premium Sea-View Room | ₹5,000 | 2–5 |
| Family Suite | ₹8,000 | 3–8 |

The system maintains room information, including room category, room number, operational condition, and housekeeping status.

### 3. Room Availability

- Allows guests to select check-in and check-out dates.
- Accepts the required number of guests and room category.
- Checks room availability for the selected dates.
- Prevents invalid date selections, such as checkout dates that are not after check-in dates.
- Prevents rooms under maintenance or unavailable rooms from being assigned.

### 4. Reservation Management

- Allows authenticated guests to make reservations.
- Validates booking dates and guest capacity.
- Stores reservation details in SQLite.
- Maintains guest information and occupant details.
- Supports reservation retrieval and cancellation.
- Maintains booking-related status information.

### 5. Payment Management

- Includes a payment-related workflow connected to reservations.
- Handles payment-related information and booking payment attempts.
- Supports validation of payment-related operations.
- Maintains the connection between reservation and payment processing.

### 6. Billing and PDF Receipt Generation

- Generates a billing receipt in PDF format after a successful room booking.
- Includes important reservation and billing information, such as:
  - Guest details
  - Reservation details
  - Room number
  - Room category
  - Check-in and check-out dates
  - Price details
  - Details of all occupants staying in the same room

### 7. Staff Authentication and Role-Based Access

The system provides three different staff roles.

| Staff Role | Main Responsibilities |
|---|---|
| **Administrator** | Manages and monitors hotel operations, staff-related access, housekeeping information, and maintenance activities. |
| **Receptionist** | Handles guest-related operations, reservations, room information, and front desk activities. |
| **Housekeeping Staff** | Views assigned rooms and manages housekeeping and room cleaning activities. |

Role-based access control ensures that staff members can access only the dashboards and operations permitted for their roles.

### 8. Housekeeping Management

- Provides a housekeeping dashboard for assigned rooms.
- Allows housekeeping staff to update room cleaning statuses.
- Maintains the following room housekeeping statuses:

| Status | Description |
|---|---|
| **Dirty / Vacant** | Room is vacant but requires cleaning. |
| **Cleaning In Progress** | Housekeeping staff are currently cleaning the room. |
| **Clean / Ready** | Room has been cleaned and is ready for front desk check-in. |

- Allows housekeeping staff to report rooms that need repair.
- Prevents rooms that are not ready from being treated as available for check-in.
- Allows authorized staff to view housekeeping information according to their roles.

### 9. Maintenance Management

- Allows maintenance issues to be reported.
- Stores maintenance-related information.
- Marks affected rooms as under maintenance.
- Prevents rooms under maintenance from being assigned to new reservations.
- Allows maintenance reports to be resolved.
- Restores the room's operational status after the maintenance issue is resolved.

### 10. Seasonal Pricing

- Supports seasonal room pricing.
- Maintains seasonal pricing information in the database.
- Allows room rates to be calculated according to applicable seasonal pricing rules and booking dates.

### 11. Staff Logout

- Provides a logout option on staff dashboards.
- Clears the active staff session.
- Redirects staff members to the staff login page after logout.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.13.0** | Main programming language used for application logic and backend development. |
| **Flask 3.1.3** | Python web framework used to develop the web application and routes. |
| **SQLite 3.45.3** | Database used to store hotel, guest, reservation, and staff information. |
| **HTML5** | Used to structure web pages. |
| **CSS3** | Used to style the application interface. |
| **bcrypt** | Used for password hashing and secure password verification. |
| **ReportLab** | Used to generate PDF billing receipts. |
| **pytest** | Used for automated unit and integration testing. |
| **pytest-cov** | Used to measure test coverage. |
| **Coverage.py** | Used to generate code coverage reports. |
| **Visual Studio Code** | Development environment. |
| **Git and GitHub** | Version control and project repository hosting. |

---

## 💻 Installation and Setup

Follow these steps to run the Hotel Booking and Reservation Management System locally.

### 1. Clone the Repository

Clone the project from GitHub:

```bash
git clone <https://github.com/Falak-star18/Hotel_Booking_Reservation_System.git>
```

### 2. Navigate to the Project Folder

```bash
cd Hotel_Booking_Reservation_System
```

### 3. Verify Python Installation

Ensure that Python 3.13.0 or a compatible Python version is installed.

```bash
python --version
```

### 4. Create a Virtual Environment

```bash
python -m venv .venv
```

### 5. Activate the Virtual Environment

For Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 6. Install Required Libraries

```bash
pip install Flask bcrypt reportlab pytest pytest-cov
```

### 7. Initialize the Database

If the database has not already been initialized, run the database initialization script:

```bash
python database/init_db.py
```

### 8. Run the Flask Application

```bash
python app.py
```

After starting the application, open the following address in your browser:

```text
http://127.0.0.1:5000
```

---

## 🧪 Usage and Testing

The project uses **pytest** to verify the correctness and reliability of its individual modules and integrated workflows.

The test cases cover authentication, access control, room management, reservations, billing, payments, housekeeping, maintenance, and integration between different modules.

### Running Individual Test Files

To execute a particular test file:

```bash
python -m pytest tests/test_auth.py -v
```

Other test files can be executed using the same format:

```bash
python -m pytest tests/test_access.py -v
python -m pytest tests/test_bookings.py -v
python -m pytest tests/test_rooms.py -v
python -m pytest tests/test_billing.py -v
python -m pytest tests/test_payments.py -v
python -m pytest tests/test_housekeeping.py -v
python -m pytest tests/test_maintenance.py -v
python -m pytest tests/test_integration.py -v
```

### Running All Test Cases

To execute the complete test suite:

```bash
python -m pytest tests/ -v
```

### Generating the Coverage Report

To measure code coverage and generate an HTML report:

```bash
python -m pytest --cov=app --cov=database --cov-report=term-missing --cov-report=html
```

To open the HTML coverage report on Windows:

```powershell
start htmlcov\index.html
```

### Testing Results

The completed test execution produced the following results:

| Testing Metric | Result |
|---|---:|
| Total Test Cases Passed | **130** |
| Test Cases Failed | **0** |
| Application (`app.py`) Coverage | **77%** |
| Overall Coverage | **54%** |

All 130 test cases passed successfully during the reported test run.

The HTML coverage report was also generated to identify executed and unexecuted lines of code.

---

## 📁 Project Structure

The project is organized into application, database, template, static, and testing components.

```text
Hotel_Booking_Reservation_System/
│
├── app.py
│
├── database/
│   ├── db.py
│   ├── init_db.py
│   ├── seed_data.py
│   ├── add_rooms.py
│   ├── add_users.py
│   └── other database scripts
│
├── tests/
│   ├── test_access.py
│   ├── test_auth.py
│   ├── test_bookings.py
│   ├── test_rooms.py
│   ├── test_billing.py
│   ├── test_payments.py
│   ├── test_housekeeping.py
│   ├── test_maintenance.py
│   └── test_integration.py
│
├── templates/
│   └── HTML templates
│
├── static/
│   ├── css/
│   └── images/
│
├── htmlcov/
│   └── HTML coverage report
│
└── README.md
```

*Note: This is a simplified overview of the main project components. Additional files and folders may be present in the actual repository.*

---

## 🚀 Future Enhancements

The system can be extended with additional functionalities in the future.

| Feature | Description |
|---|---|
| **Multiple Hotel Support** | Extend the application to manage multiple hotels and their reservations. |
| **Advanced Reporting** | Generate detailed reports related to bookings, revenue, room occupancy, and hotel operations. |
| **Email Notifications** | Send booking confirmations, cancellation notifications, and other updates through email. |
| **Enhanced Payment Integration** | Integrate a secure online payment gateway for processing guest payments. |
| **Customer Reviews and Ratings** | Allow guests to provide feedback and ratings after their stay. |
| **Advanced Dashboard Analytics** | Provide graphical representations of hotel occupancy, bookings, and revenue. |
| **Improved Booking Management** | Introduce additional booking management options and automated notifications. |

---

## 👩‍💻 Author

![Author: Falak Sardar](https://img.shields.io/badge/Author-Falak_Sardar-orange)

Developed as part of an academic **Software Engineering project**.

**Project:** Hotel Booking and Reservation Management System

**Domain:** Hotel and Hospitality Management

**Development Model:** Agile Software Development Life Cycle (SDLC)

**Tools and Technologies:** Python | Flask | SQLite | HTML | CSS | pytest | Git | GitHub

🔗 **GitHub Profile:** [Falak-star18](https://github.com/Falak-star18)

---

## 📌 Project Information

This project demonstrates the application of software engineering concepts, modular development, database management, role-based access control, and automated testing in a practical hotel management scenario.

The system aims to make hotel operations more organized, efficient, and reliable by bringing essential reservation and hotel management activities together in one application.

![Python](https://img.shields.io/badge/Python-3.13.0-blue)
![Flask](https://img.shields.io/badge/Flask-3.1.3-black)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue)
![HTML5](https://img.shields.io/badge/HTML5-HTML-orange)
![CSS3](https://img.shields.io/badge/CSS3-CSS-blue)
![bcrypt](https://img.shields.io/badge/Security-bcrypt-green)
![ReportLab](https://img.shields.io/badge/PDF-ReportLab-red)
![pytest](https://img.shields.io/badge/Testing-pytest-brightgreen)
![pytest-cov](https://img.shields.io/badge/Coverage-pytest--cov-yellow)
![VS Code](https://img.shields.io/badge/Code_Editor-VS%20Code-blueviolet)
![Git](https://img.shields.io/badge/Version_Control-Git-orange)

[![Hotel Booking and Reservation Management System](https://img.shields.io/badge/Hotel_Booking_Management_System-Project-brightgreen)](https://github.com/Falak-star18/Hotel_Booking_Reservation_System.git)

[![GitHub Repository](https://img.shields.io/badge/GitHub_Repository-Hotel_Booking_Reservation_System-yellow)](https://github.com/Falak-star18/Hotel_Booking_Reservation_System.git)