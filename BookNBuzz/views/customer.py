"""
views/customer.py - customer-facing View blueprint.

Use cases: Browse Packages, Choose Service Mode, Make Booking (Select Time Slot
+ Service Address), View My Bookings, Cancel Booking, View Notifications.
"""

from datetime import date as date_cls, datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort)

from model import Service, Booking, Availability, Barber, Notification
from auth_utils import login_required, current_user

customer_bp = Blueprint("customer", __name__)


# --------------------------------------------------------------------------- #
#  Landing / hero page
# --------------------------------------------------------------------------- #
@customer_bp.route("/home")
def home():
    services = Service.all(active_only=True)
    return render_template("customer/home.html", services=services[:3])


# --------------------------------------------------------------------------- #
#  Browse Packages
# --------------------------------------------------------------------------- #
@customer_bp.route("/packages")
def packages():
    services = Service.all(active_only=True)
    return render_template("customer/packages.html", services=services)


@customer_bp.route("/packages/<int:service_id>")
def service_detail(service_id):
    service = Service.get(service_id)
    if service is None or not service.active:
        abort(404)
    return render_template("customer/service_detail.html", service=service)


# --------------------------------------------------------------------------- #
#  Make Booking  (Choose Service Mode + Select Time Slot + Service Address)
# --------------------------------------------------------------------------- #
@customer_bp.route("/book/<int:service_id>", methods=["GET"])
@login_required
def book(service_id):
    """Step 1+2: pick mode + date, then the page shows the open time slots."""
    service = Service.get(service_id)
    if service is None or not service.active:
        abort(404)

    barber = Barber.first()
    if barber is None:
        flash("No barber is available right now. Please try again later.", "error")
        return redirect(url_for("customer.packages"))

    mode = request.args.get("mode", "walk_in")
    selected_date = request.args.get("date", "")
    today = date_cls.today().isoformat()
    slots = []
    searched = False

    if selected_date:
        searched = True
        # Don't allow booking in the past or on a blocked date.
        if selected_date < today:
            flash("Please choose today or a future date.", "error")
        elif Availability.is_blocked_date(barber.id, selected_date):
            flash("That date is unavailable. Please choose another.", "error")
        else:
            slots = Availability.open_slots(
                barber.id, selected_date, service.duration_minutes)

    return render_template(
        "customer/book.html", service=service, barber=barber,
        mode=mode, selected_date=selected_date,
        selected_date_label=_pretty_date(selected_date), slots=slots,
        searched=searched, today=today,
        blocked_dates=Availability.blocked_dates(barber.id),
        working_weekdays=Availability.working_weekdays(barber.id))


def _pretty_date(iso_date):
    """'2026-06-25' -> 'Thu, 25 June' (empty string for blank/invalid)."""
    if not iso_date:
        return ""
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return ""
    # %-d isn't portable (Windows), so build the day number by hand.
    return d.strftime("%a, ") + str(d.day) + d.strftime(" %B")


@customer_bp.route("/book/<int:service_id>/slots", methods=["GET"])
@login_required
def book_slots(service_id):
    """JSON: open time slots for a date, so the page can load them on date
    click without a full reload. Mirrors the validation in book()."""
    service = Service.get(service_id)
    if service is None or not service.active:
        abort(404)

    barber = Barber.first()
    selected_date = request.args.get("date", "")
    today = date_cls.today().isoformat()

    slots = []
    if (barber is not None and selected_date and selected_date >= today
            and not Availability.is_blocked_date(barber.id, selected_date)):
        slots = Availability.open_slots(
            barber.id, selected_date, service.duration_minutes)

    return {"date": selected_date, "label": _pretty_date(selected_date),
            "slots": slots}


@customer_bp.route("/book/<int:service_id>/confirm", methods=["POST"])
@login_required
def confirm_booking(service_id):
    """Step 3: validate everything and save the booking as 'pending'."""
    service = Service.get(service_id)
    if service is None or not service.active:
        abort(404)

    barber = Barber.first()
    if barber is None:
        flash("No barber is available right now.", "error")
        return redirect(url_for("customer.packages"))

    mode = request.form.get("mode", "walk_in")
    booking_date = request.form.get("date", "")
    time_slot = request.form.get("time_slot", "")
    service_address = request.form.get("service_address", "").strip()

    errors = []
    if mode not in ("walk_in", "mobile"):
        errors.append("Please choose a valid service mode.")
    if not booking_date or booking_date < date_cls.today().isoformat():
        errors.append("Please choose today or a future date.")
    elif Availability.is_blocked_date(barber.id, booking_date):
        errors.append("That date is unavailable. Please choose another.")
    if not time_slot:
        errors.append("Please select a time slot.")
    if mode == "mobile" and not service_address:
        errors.append("A service address is required for mobile bookings.")

    # Re-validate the slot is still inside availability and free.
    if not errors:
        open_now = Availability.open_slots(
            barber.id, booking_date, service.duration_minutes)
        if time_slot not in open_now:
            errors.append("Sorry, that time slot was just taken. Pick another.")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("customer.book", service_id=service_id,
                                mode=mode, date=booking_date))

    user = current_user()
    booking = Booking(
        customer_id=user.id, barber_id=None, service_id=service.id,
        mode=mode, date=booking_date, time_slot=time_slot,
        service_address=service_address if mode == "mobile" else None,
        status="pending", total_price=service.price)
    booking.save()

    # Notify the customer that their request is in.
    Notification.push(
        user.id,
        f"Booking requested: {service.name} on {booking_date} at {time_slot}. "
        f"Status is pending confirmation.")

    flash("Booking requested! You'll be notified when the barber confirms.",
          "success")
    return redirect(url_for("customer.my_bookings"))


# --------------------------------------------------------------------------- #
#  View My Bookings
# --------------------------------------------------------------------------- #
@customer_bp.route("/my-bookings")
@login_required
def my_bookings():
    user = current_user()
    bookings = Booking.for_customer(user.id)
    return render_template("customer/my_bookings.html", bookings=bookings)


# --------------------------------------------------------------------------- #
#  Cancel Booking
# --------------------------------------------------------------------------- #
@customer_bp.route("/my-bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    user = current_user()
    booking = Booking.get(booking_id)
    if booking is None or booking["customer_id"] != user.id:
        abort(404)
    if booking["status"] not in ("pending", "confirmed"):
        flash("This booking can no longer be cancelled.", "error")
    else:
        Booking.cancel(booking_id, user.id)
        Notification.push(
            user.id,
            f"You cancelled your {booking['service_name']} booking on "
            f"{booking['date']} at {booking['time_slot']}.")
        flash("Booking cancelled.", "success")
    return redirect(url_for("customer.my_bookings"))


# --------------------------------------------------------------------------- #
#  View Notifications
# --------------------------------------------------------------------------- #
@customer_bp.route("/notifications")
@login_required
def notifications():
    user = current_user()
    items = Notification.for_user(user.id)
    Notification.mark_all_read(user.id)  # opening the page clears the badge
    return render_template("customer/notifications.html", notifications=items)
