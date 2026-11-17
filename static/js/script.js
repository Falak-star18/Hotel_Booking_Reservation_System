// ----------------------------------------
// 1. Get Booking Form Date Fields
// ----------------------------------------

const checkin = document.getElementById("checkin");
const checkout = document.getElementById("checkout");

// ----------------------------------------
// 2. Prevent Selection of Past Dates
// ----------------------------------------

const today = new Date();

const todayString =
    today.getFullYear() + "-" +
    String(today.getMonth() + 1).padStart(2, "0") + "-" +
    String(today.getDate()).padStart(2, "0");

checkin.min = todayString;
checkout.min = todayString;

// ----------------------------------------
// 3. Update Minimum Check-out Date
// ----------------------------------------

checkin.addEventListener("change", function () {

    checkout.min = checkin.value;

    if (checkout.value && checkout.value <= checkin.value) {
        checkout.value = "";
    }

});

// ----------------------------------------
// 4. Validate Check-in and Check-out Dates
// ----------------------------------------

const bookingForm = document.querySelector(".booking-form");

bookingForm.addEventListener("submit", function (event) {

    if (!checkin.value || !checkout.value) {
        event.preventDefault();
        alert("Please select both check-in and check-out dates.");
        return;
    }

    if (checkout.value <= checkin.value) {
        event.preventDefault();
        alert("Check-out date must be later than check-in date.");
        checkout.value = "";
        return;
    }

});