"""Barber area - Manage Bookings + confirm / claim / release / update status."""

from datetime import date as date_cls, timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from bookings.decorators import barber_required
from bookings.models import Booking, Notification
from bookings.views.helpers import back, parse_iso


@barber_required
def bookings(request):
    counts = Booking.counts_by_date()
    pending_total = Booking.pending_count()

    # "Pending (all dates)" tab.
    if request.GET.get("view") == "pending":
        return render(request, "barber/bookings.html", {
            "mode": "pending", "bookings": Booking.pending_all(),
            "counts": counts, "pending_total": pending_total,
            "statuses": Booking.STATUSES, "active_status": "all",
        })

    # Per-date view (defaults to today).
    today = date_cls.today()
    sel_obj = parse_iso(request.GET.get("date", "")) or today
    sel = sel_obj.isoformat()

    day_all = list(Booking.for_day(sel_obj))
    status = request.GET.get("status") or None
    items = [b for b in day_all if b.status == status] if status else day_all

    return render(request, "barber/bookings.html", {
        "mode": "date", "bookings": items, "sel_date": sel,
        "pretty": sel_obj.strftime("%A, %d %B %Y"), "day_count": len(day_all),
        "prev_date": (sel_obj - timedelta(days=1)).isoformat(),
        "next_date": (sel_obj + timedelta(days=1)).isoformat(),
        "today": today.isoformat(), "counts": counts,
        "pending_total": pending_total,
        "active_status": status or "all", "statuses": Booking.STATUSES,
    })


@barber_required
def barber_confirm_booking(request, booking_id):
    if request.method != "POST":
        return redirect("barber_bookings")
    barber = request.user
    booking = get_object_or_404(Booking, pk=booking_id)
    if booking.barber_id != barber.id:
        messages.error(request, "You can only confirm bookings assigned to you.")
    elif booking.status != "pending":
        messages.error(request, "Only a pending booking can be confirmed.")
    elif Booking.confirm(booking_id, barber):
        Notification.push(
            booking.customer,
            f"{barber.name} confirmed your {booking.service_name} booking on "
            f"{booking.date.isoformat()} at {booking.time_slot}. See you then!")
        messages.success(request, f"Booking #{booking_id} confirmed.")
    else:
        messages.error(request, "Could not confirm that booking.")
    return redirect(back(request, "/barber/bookings"))


@barber_required
def claim_booking(request, booking_id):
    if request.method != "POST":
        return redirect("barber_bookings")
    barber = request.user
    booking = get_object_or_404(Booking, pk=booking_id)
    if booking.barber_id is not None:
        messages.error(request,
                       f"That booking is already claimed by {booking.barber_name}.")
    elif Booking.claim(booking_id, barber):
        Notification.push(
            booking.customer,
            f"{barber.name} confirmed your {booking.service_name} booking on "
            f"{booking.date.isoformat()} at {booking.time_slot}. See you then!")
        messages.success(request,
                         f"You claimed booking #{booking_id} - it is now confirmed.")
    else:
        messages.error(request,
                       "Could not claim that booking - someone may have just taken it.")
    return redirect(back(request, "/barber/bookings"))


@barber_required
def release_booking(request, booking_id):
    if request.method != "POST":
        return redirect("barber_bookings")
    barber = request.user
    booking = get_object_or_404(Booking, pk=booking_id)
    if booking.barber_id != barber.id:
        messages.error(request, "You can only release a booking you have claimed.")
    elif booking.status != "confirmed":
        messages.error(request, "Only a confirmed booking can be released.")
    else:
        Booking.release(booking_id, barber)
        Notification.push(
            booking.customer,
            f"Your {booking.service_name} booking on {booking.date.isoformat()} "
            f"at {booking.time_slot} is back to PENDING and awaiting a barber.")
        messages.success(request,
                         f"Booking #{booking_id} released - back to pending.")
    return redirect(back(request, "/barber/bookings"))


@barber_required
def update_status(request, booking_id):
    if request.method != "POST":
        return redirect("barber_bookings")
    barber = request.user
    booking = get_object_or_404(Booking, pk=booking_id)

    if booking.barber_id != barber.id:
        messages.error(request, "You can only update bookings you have claimed.")
        return redirect(back(request, "/barber/bookings"))

    new_status = request.POST.get("status", "")
    if new_status not in ("completed", "cancelled"):
        messages.error(request, "You can only mark a booking completed or cancelled.")
        return redirect(back(request, "/barber/bookings"))
    if booking.status != "confirmed":
        messages.error(request, "Claim the booking first - only confirmed "
                                "bookings can be completed or cancelled.")
        return redirect(back(request, "/barber/bookings"))

    Booking.set_status(booking_id, new_status)
    Notification.push(
        booking.customer,
        f"Your {booking.service_name} booking on {booking.date.isoformat()} at "
        f"{booking.time_slot} is now {new_status.upper()}.")
    messages.success(request, f"Booking #{booking_id} marked {new_status}.")
    return redirect(back(request, "/barber/bookings"))
