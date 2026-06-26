"""Barber area - Manage Availability (weekly hours + block days)."""

from datetime import date as date_cls

from django.contrib import messages
from django.shortcuts import redirect, render

from bookings.decorators import barber_required
from bookings.models import Availability
from bookings.views.helpers import WEEKDAYS, parse_iso


@barber_required
def availability(request):
    barber = request.user
    schedule = Availability.weekly_schedule(barber)
    for d in schedule:
        d["name"] = WEEKDAYS[d["weekday"]]
    return render(request, "barber/availability.html", {
        "schedule": schedule,
        "weekdays": WEEKDAYS,
        "blocked_dates": Availability.blocked_dates(barber),
        "today": date_cls.today().isoformat(),
    })


@barber_required
def set_weekday(request):
    if request.method != "POST":
        return redirect("barber_availability")
    barber = request.user
    try:
        weekday = int(request.POST.get("weekday"))
        assert 0 <= weekday <= 6
    except (TypeError, ValueError, AssertionError):
        messages.error(request, "Invalid day.")
        return redirect("barber_availability")

    if request.POST.get("open") != "on":
        Availability.clear_weekday(barber, weekday)
        messages.success(request, f"{WEEKDAYS[weekday]} set to closed.")
        return redirect("barber_availability")

    start = request.POST.get("start_time") or "09:00"
    end = request.POST.get("end_time") or "17:00"
    if start >= end:
        messages.error(request, "Start time must be before end time.")
        return redirect("barber_availability")

    Availability.set_weekday(barber, weekday, start, end)
    messages.success(request, f"{WEEKDAYS[weekday]} hours saved ({start}–{end}).")
    return redirect("barber_availability")


@barber_required
def toggle_block(request):
    if request.method != "POST":
        return redirect("barber_availability")
    barber = request.user
    raw = request.POST.get("date", "")
    chosen = parse_iso(raw)
    if chosen is None:
        messages.error(request, "Invalid date.")
        return redirect("barber_availability")

    if chosen < date_cls.today():
        messages.error(request, "You can't block a date in the past.")
        return redirect("barber_availability")

    now_blocked = Availability.toggle_block(barber, chosen)
    messages.success(request,
                     f"{raw} {'blocked - no bookings' if now_blocked else 'unblocked'}.")
    return redirect("barber_availability")
