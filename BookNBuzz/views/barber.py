"""
views/barber.py - barber/admin View blueprint.

Use cases: View Dashboard, Manage Customers, Manage Items & Services (CRUD),
View Sales, Create Barber Account, Manage Availability, Manage Bookings,
Update Booking Status (-> creates a customer Notification).
"""

import re
from datetime import date as date_cls, datetime, timedelta

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort)

from model import (Service, Booking, Availability, Barber, Customer, User,
                   Notification)
from auth_utils import barber_required, current_user
from profile_service import apply_account_update
import db

barber_bp = Blueprint("barber", __name__, url_prefix="/barber")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]


# --------------------------------------------------------------------------- #
#  View Dashboard
# --------------------------------------------------------------------------- #
@barber_bp.route("/dashboard")
@barber_required
def dashboard():
    barber = current_user()
    stats = barber.dashboard_stats()
    todays = barber.todays_bookings()
    return render_template("barber/dashboard.html", stats=stats, todays=todays)


# --------------------------------------------------------------------------- #
#  Manage Customers
# --------------------------------------------------------------------------- #
@barber_bp.route("/customers")
@barber_required
def customers():
    rows = db.query(
        """SELECT u.id, u.name, u.email, u.phone,
                  COUNT(b.id) AS booking_count
           FROM users u
           LEFT JOIN bookings b ON b.customer_id = u.id
           WHERE u.role = 'customer'
           GROUP BY u.id
           ORDER BY u.name""")
    return render_template("barber/customers.html", customers=rows)


# --------------------------------------------------------------------------- #
#  Manage Items & Services  (CRUD)
# --------------------------------------------------------------------------- #
@barber_bp.route("/services")
@barber_required
def services():
    return render_template("barber/services.html", services=Service.all())


@barber_bp.route("/services/new", methods=["GET", "POST"])
@barber_required
def service_new():
    if request.method == "POST":
        return _save_service(None)
    return render_template("barber/service_form.html", service=None, action="new")


@barber_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@barber_required
def service_edit(service_id):
    service = Service.get(service_id)
    if service is None:
        abort(404)
    if request.method == "POST":
        return _save_service(service)
    return render_template("barber/service_form.html", service=service, action="edit")


def _save_service(service):
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    image = request.form.get("image", "").strip()
    active = 1 if request.form.get("active") == "on" else 0

    errors = []
    if not name:
        errors.append("Service name is required.")
    try:
        duration = int(request.form.get("duration_minutes", "0"))
        if duration <= 0:
            raise ValueError
    except ValueError:
        errors.append("Duration must be a positive whole number of minutes.")
        duration = 30
    try:
        price = float(request.form.get("price", "0"))
        if price < 0:
            raise ValueError
    except ValueError:
        errors.append("Price must be a valid non-negative number.")
        price = 0.0

    if errors:
        for e in errors:
            flash(e, "error")
        draft = service or Service()
        draft.name, draft.description = name, description
        draft.duration_minutes, draft.price = duration, price
        draft.image, draft.active = image, active
        action = "edit" if service else "new"
        return render_template("barber/service_form.html", service=draft, action=action)

    if service is None:
        service = Service()
    service.name = name
    service.description = description
    service.duration_minutes = duration
    service.price = price
    service.image = image or "default.svg"
    service.active = active
    service.save()
    flash("Service saved.", "success")
    return redirect(url_for("barber.services"))


@barber_bp.route("/services/<int:service_id>/delete", methods=["POST"])
@barber_required
def service_delete(service_id):
    if Service.get(service_id) is None:
        abort(404)
    Service.delete(service_id)
    flash("Service deleted.", "success")
    return redirect(url_for("barber.services"))


# --------------------------------------------------------------------------- #
#  View Sales  (revenue report from completed bookings)
# --------------------------------------------------------------------------- #
@barber_bp.route("/sales")
@barber_required
def sales():
    rows, total = Booking.sales_report()
    completed = db.query(
        "SELECT COUNT(*) AS c FROM bookings WHERE status = 'completed'",
        one=True)["c"]
    return render_template("barber/sales.html", rows=rows, total=total,
                           completed=completed)


# --------------------------------------------------------------------------- #
#  Create Barber Account
# --------------------------------------------------------------------------- #
@barber_bp.route("/barbers/new", methods=["GET", "POST"])
@barber_required
def barber_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        errors = []
        if not name:
            errors.append("Name is required.")
        if not EMAIL_RE.match(email):
            errors.append("A valid email is required.")
        elif User.email_exists(email):
            errors.append("That email is already in use.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("barber/barber_form.html",
                                   form={"name": name, "email": email, "phone": phone})

        barber = Barber(name=name, email=email, phone=phone)
        barber.set_password(password)
        barber.save()
        flash(f"Barber account created for {name}.", "success")
        return redirect(url_for("barber.dashboard"))

    return render_template("barber/barber_form.html", form={})


# --------------------------------------------------------------------------- #
#  Profile  (view + update own details / password)
# --------------------------------------------------------------------------- #
@barber_bp.route("/profile", methods=["GET", "POST"])
@barber_required
def profile():
    barber = current_user()
    if request.method == "POST":
        apply_account_update(barber)  # validates, persists + flashes
        return redirect(url_for("barber.profile"))

    return render_template("barber/profile.html",
                           action_url=url_for("barber.profile"))


# --------------------------------------------------------------------------- #
#  Manage Availability  (working hours / block days)
# --------------------------------------------------------------------------- #
@barber_bp.route("/availability")
@barber_required
def availability():
    barber = current_user()
    return render_template(
        "barber/availability.html",
        schedule=Availability.weekly_schedule(barber.id),
        weekdays=WEEKDAYS,
        blocked_dates=Availability.blocked_dates(barber.id),
        today=date_cls.today().isoformat())


@barber_bp.route("/availability/weekday", methods=["POST"])
@barber_required
def set_weekday():
    """Open/close a weekday or save its hours (in-place weekly schedule row)."""
    barber = current_user()
    try:
        weekday = int(request.form.get("weekday"))
        assert 0 <= weekday <= 6
    except (TypeError, ValueError, AssertionError):
        flash("Invalid day.", "error")
        return redirect(url_for("barber.availability"))

    if request.form.get("open") != "on":
        # Toggling a day off simply removes its working hours.
        Availability.clear_weekday(barber.id, weekday)
        flash(f"{WEEKDAYS[weekday]} set to closed.", "success")
        return redirect(url_for("barber.availability"))

    start = request.form.get("start_time") or "09:00"
    end = request.form.get("end_time") or "17:00"
    if start >= end:
        flash("Start time must be before end time.", "error")
        return redirect(url_for("barber.availability"))

    Availability.set_weekday(barber.id, weekday, start, end)
    flash(f"{WEEKDAYS[weekday]} hours saved ({start}–{end}).", "success")
    return redirect(url_for("barber.availability"))


@barber_bp.route("/availability/block-toggle", methods=["POST"])
@barber_required
def toggle_block():
    """Toggle a single calendar date blocked/unblocked."""
    barber = current_user()
    raw = request.form.get("date", "")
    try:
        chosen = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date.", "error")
        return redirect(url_for("barber.availability"))

    if chosen < date_cls.today():
        flash("You can't block a date in the past.", "error")
        return redirect(url_for("barber.availability"))

    now_blocked = Availability.toggle_block(barber.id, raw)
    flash(f"{raw} {'blocked - no bookings' if now_blocked else 'unblocked'}.",
          "success")
    return redirect(url_for("barber.availability"))


# --------------------------------------------------------------------------- #
#  Manage Bookings  +  Update Booking Status
# --------------------------------------------------------------------------- #
@barber_bp.route("/bookings")
@barber_required
def bookings():
    counts = Booking.counts_by_date()
    pending_total = Booking.pending_count()

    # "Pending (all dates)" tab - ignores the selected date so nothing that
    # needs action gets lost on a future day.
    if request.args.get("view") == "pending":
        return render_template(
            "barber/bookings.html", mode="pending",
            bookings=Booking.pending_all(), counts=counts,
            pending_total=pending_total, statuses=Booking.STATUSES,
            active_status="all")

    # Per-date view (defaults to today).
    today = date_cls.today().isoformat()
    sel = request.args.get("date") or today
    try:
        d = datetime.strptime(sel, "%Y-%m-%d").date()
    except ValueError:
        d = date_cls.today()
        sel = today

    day_all = Booking.for_day(sel)               # all statuses for the day
    status = request.args.get("status") or None
    items = [b for b in day_all if b["status"] == status] if status else day_all

    return render_template(
        "barber/bookings.html", mode="date", bookings=items,
        sel_date=sel, pretty=d.strftime("%A, %d %B %Y"), day_count=len(day_all),
        prev_date=(d - timedelta(days=1)).isoformat(),
        next_date=(d + timedelta(days=1)).isoformat(),
        today=today, counts=counts, pending_total=pending_total,
        active_status=status or "all", statuses=Booking.STATUSES)


@barber_bp.route("/bookings/<int:booking_id>/confirm", methods=["POST"])
@barber_required
def confirm_booking(booking_id):
    """Confirm a pending booking the customer assigned to this barber.

    Customers now choose their barber, so new bookings arrive already assigned
    and pending. The owning barber accepts them here (pending -> confirmed).
    """
    barber = current_user()
    booking = Booking.get(booking_id)
    if booking is None:
        abort(404)
    if booking["barber_id"] != barber.id:
        flash("You can only confirm bookings assigned to you.", "error")
    elif booking["status"] != "pending":
        flash("Only a pending booking can be confirmed.", "error")
    elif Booking.confirm(booking_id, barber.id):
        Notification.push(
            booking["customer_id"],
            f"{barber.name} confirmed your {booking['service_name']} booking on "
            f"{booking['date']} at {booking['time_slot']}. See you then!")
        flash(f"Booking #{booking_id} confirmed.", "success")
    else:
        flash("Could not confirm that booking.", "error")
    return redirect(request.referrer or url_for("barber.bookings"))


@barber_bp.route("/bookings/<int:booking_id>/claim", methods=["POST"])
@barber_required
def claim_booking(booking_id):
    barber = current_user()
    booking = Booking.get(booking_id)
    if booking is None:
        abort(404)
    if booking["barber_id"] is not None:
        flash(f"That booking is already claimed by {booking['barber_name']}.",
              "error")
    elif Booking.claim(booking_id, barber.id):
        # Claiming confirms the booking (pending -> confirmed).
        Notification.push(
            booking["customer_id"],
            f"{barber.name} confirmed your {booking['service_name']} booking on "
            f"{booking['date']} at {booking['time_slot']}. See you then!")
        flash(f"You claimed booking #{booking_id} - it is now confirmed.",
              "success")
    else:
        flash("Could not claim that booking - someone may have just taken it.",
              "error")
    return redirect(request.referrer or url_for("barber.bookings"))


@barber_bp.route("/bookings/<int:booking_id>/release", methods=["POST"])
@barber_required
def release_booking(booking_id):
    barber = current_user()
    booking = Booking.get(booking_id)
    if booking is None:
        abort(404)
    if booking["barber_id"] != barber.id:
        flash("You can only release a booking you have claimed.", "error")
    elif booking["status"] != "confirmed":
        flash("Only a confirmed booking can be released.", "error")
    else:
        # Releasing reverts the booking to pending and unclaims it.
        Booking.release(booking_id, barber.id)
        Notification.push(
            booking["customer_id"],
            f"Your {booking['service_name']} booking on {booking['date']} at "
            f"{booking['time_slot']} is back to PENDING and awaiting a barber.")
        flash(f"Booking #{booking_id} released - back to pending.", "success")
    return redirect(request.referrer or url_for("barber.bookings"))


@barber_bp.route("/bookings/<int:booking_id>/status", methods=["POST"])
@barber_required
def update_status(booking_id):
    # The dropdown only finalises a CONFIRMED (claimed) booking as
    # completed or cancelled. Pending->Confirmed is done by claiming instead.
    barber = current_user()
    booking = Booking.get(booking_id)
    if booking is None:
        abort(404)

    # A barber may only update bookings they have claimed - no interfering
    # with another barber's appointments.
    if booking["barber_id"] != barber.id:
        flash("You can only update bookings you have claimed.", "error")
        return redirect(request.referrer or url_for("barber.bookings"))

    new_status = request.form.get("status", "")
    if new_status not in ("completed", "cancelled"):
        flash("You can only mark a booking completed or cancelled.", "error")
        return redirect(request.referrer or url_for("barber.bookings"))
    if booking["status"] != "confirmed":
        flash("Claim the booking first - only confirmed bookings can be "
              "completed or cancelled.", "error")
        return redirect(request.referrer or url_for("barber.bookings"))

    Booking.set_status(booking_id, new_status)

    # Updating the status raises a Notification for the customer.
    Notification.push(
        booking["customer_id"],
        f"Your {booking['service_name']} booking on {booking['date']} at "
        f"{booking['time_slot']} is now {new_status.upper()}.")

    flash(f"Booking #{booking_id} marked {new_status}.", "success")
    return redirect(request.referrer or url_for("barber.bookings"))
