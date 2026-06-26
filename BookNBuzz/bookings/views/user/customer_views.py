"""
User area - customer use cases: Browse Packages, Make Booking (pick barber ->
date & time -> confirm), View My Bookings, Cancel Booking, Notifications,
My Account.
"""

from datetime import date as date_cls

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from bookings.models import (Availability, Booking, MOBILE_SERVICE_FEE,
                             Notification, Service, User)
from bookings.profile_service import apply_account_update
from bookings.views.helpers import (active_service_or_404, get_barber,
                                    parse_iso, pretty_date)


def home(request):
    services = list(Service.objects.filter(active=True))
    return render(request, "user/home.html", {"services": services[:3]})


def packages(request):
    services = Service.objects.filter(active=True)
    return render(request, "user/packages.html", {"services": services})


def service_detail(request, service_id):
    service = active_service_or_404(service_id)
    return render(request, "user/service_detail.html", {"service": service})


# ---- Make Booking: pick barber -> date & time -> confirm ------------------
@login_required
def book(request, service_id):
    """Step 1: pick which barber to book with."""
    service = active_service_or_404(service_id)

    barbers = User.objects.filter(role="barber").order_by("name")
    if not barbers:
        messages.error(request,
                       "No barber is available right now. Please try again later.")
        return redirect("customer_packages")

    return render(request, "user/book_barber.html",
                  {"service": service, "barbers": barbers})


@login_required
def book_times(request, service_id, barber_id):
    """Step 2: pick mode + date for the chosen barber; page shows open slots."""
    service = active_service_or_404(service_id)

    barber = get_barber(barber_id)
    if barber is None:
        messages.error(request,
                       "That barber is no longer available. Please pick another.")
        return redirect("customer_book", service_id=service_id)

    mode = request.GET.get("mode", "walk_in")
    selected_date = request.GET.get("date", "")
    today = date_cls.today()
    slots = []
    searched = False
    selected_obj = None

    if selected_date:
        searched = True
        selected_obj = parse_iso(selected_date)
        if selected_obj is None or selected_obj < today:
            messages.error(request, "Please choose today or a future date.")
        elif Availability.is_blocked_date(barber, selected_obj):
            messages.error(request, "That date is unavailable. Please choose another.")
        else:
            slots = Availability.open_slots(barber, selected_obj,
                                            service.duration_minutes)

    initial_total = service.price + (MOBILE_SERVICE_FEE if mode == "mobile" else 0)

    return render(request, "user/book.html", {
        "service": service, "barber": barber, "mode": mode,
        "selected_date": selected_date,
        "selected_date_label": pretty_date(selected_obj),
        "slots": slots, "searched": searched, "today": today.isoformat(),
        "initial_total": initial_total,
        "blocked_dates": Availability.blocked_dates(barber),
        "working_weekdays": Availability.working_weekdays(barber),
    })


@login_required
def book_slots(request, service_id):
    """JSON: a barber's open time slots for a date (loaded on date click)."""
    service = active_service_or_404(service_id)

    try:
        barber_id = int(request.GET.get("barber_id", ""))
    except (TypeError, ValueError):
        barber_id = None
    barber = get_barber(barber_id) if barber_id is not None else None
    selected_date = request.GET.get("date", "")
    selected_obj = parse_iso(selected_date)
    today = date_cls.today()

    slots = []
    if (barber is not None and selected_obj is not None
            and selected_obj >= today
            and not Availability.is_blocked_date(barber, selected_obj)):
        slots = Availability.open_slots(barber, selected_obj,
                                        service.duration_minutes)

    return JsonResponse({"date": selected_date,
                         "label": pretty_date(selected_obj), "slots": slots})


@login_required
def confirm_booking(request, service_id):
    """Step 3: validate everything server-side and save the booking."""
    if request.method != "POST":
        return redirect("customer_book", service_id=service_id)

    service = active_service_or_404(service_id)

    try:
        barber_id = int(request.POST.get("barber_id", ""))
    except (TypeError, ValueError):
        barber_id = None
    barber = get_barber(barber_id) if barber_id is not None else None
    if barber is None:
        messages.error(request, "Please pick a barber to book with.")
        return redirect("customer_book", service_id=service_id)

    mode = request.POST.get("mode", "walk_in")
    booking_date = request.POST.get("date", "")
    time_slot = request.POST.get("time_slot", "")
    service_address = request.POST.get("service_address", "").strip()
    booking_obj = parse_iso(booking_date)
    today = date_cls.today()

    errors = []
    if mode not in ("walk_in", "mobile"):
        errors.append("Please choose a valid service mode.")
    if booking_obj is None or booking_obj < today:
        errors.append("Please choose today or a future date.")
    elif Availability.is_blocked_date(barber, booking_obj):
        errors.append("That date is unavailable. Please choose another.")
    if not time_slot:
        errors.append("Please select a time slot.")
    if mode == "mobile" and not service_address:
        errors.append("A service address is required for mobile bookings.")

    # Re-validate the slot is still inside THIS barber's availability and free.
    if not errors:
        open_now = Availability.open_slots(barber, booking_obj,
                                           service.duration_minutes)
        if time_slot not in open_now:
            errors.append("Sorry, that time isn't available for this barber "
                          "anymore. Please pick another.")

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect(f"/book/{service.id}/barber/{barber.id}"
                        f"?mode={mode}&date={booking_date}")

    # Total is computed server-side (package + mobile fee) - never trusted.
    total_price = Booking.compute_total(service.price, mode)

    Booking.objects.create(
        customer=request.user, barber=barber, service=service, mode=mode,
        date=booking_obj, time_slot=time_slot,
        service_address=service_address if mode == "mobile" else None,
        status="pending", total_price=total_price)

    Notification.push(
        request.user,
        f"Booking requested with {barber.name}: {service.name} on "
        f"{booking_date} at {time_slot}. Status is pending confirmation.")

    messages.success(request, f"Booking requested with {barber.name}! You'll be "
                              f"notified when they confirm.")
    return redirect("customer_my_bookings")


@login_required
def my_bookings(request):
    bookings = Booking.for_customer(request.user)
    return render(request, "user/my_bookings.html", {"bookings": bookings})


@login_required
def cancel_booking(request, booking_id):
    if request.method != "POST":
        return redirect("customer_my_bookings")
    booking = get_object_or_404(Booking, pk=booking_id)
    if booking.customer_id != request.user.id:
        raise Http404
    if booking.status not in ("pending", "confirmed"):
        messages.error(request, "This booking can no longer be cancelled.")
    else:
        Booking.cancel(booking_id, request.user)
        Notification.push(
            request.user,
            f"You cancelled your {booking.service_name} booking on "
            f"{booking.date.isoformat()} at {booking.time_slot}.")
        messages.success(request, "Booking cancelled.")
    return redirect("customer_my_bookings")


@login_required
def notifications(request):
    items = list(Notification.for_user(request.user))
    Notification.mark_all_read(request.user)  # opening clears the badge
    return render(request, "user/notifications.html",
                  {"notifications": items})


@login_required
def account(request):
    # Barbers have their own profile page; keep this one for customers only.
    if request.user.role != "customer":
        return redirect("barber_profile")

    if request.method == "POST":
        apply_account_update(request)  # validates, persists + flashes
        return redirect("customer_account")

    return render(request, "user/account.html", {})
