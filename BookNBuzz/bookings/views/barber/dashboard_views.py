"""
Barber area - dashboard, manage customers, sales report, create barber account,
and the barber's own profile.
"""

from datetime import date as date_cls

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render

from bookings.decorators import barber_required
from bookings.models import Booking, Service, User
from bookings.profile_service import apply_account_update
from bookings.views.helpers import EMAIL_RE


@barber_required
def dashboard(request):
    stats = Booking.dashboard_stats()
    todays = Booking.for_date(date_cls.today())
    return render(request, "barber/dashboard.html",
                  {"stats": stats, "todays": todays})


@barber_required
def customers(request):
    rows = (User.objects.filter(role="customer")
            .annotate(booking_count=Count("bookings_made"))
            .order_by("name"))
    return render(request, "barber/customers.html", {"customers": rows})


@barber_required
def sales(request):
    rows, total = Booking.sales_report()
    completed = Booking.objects.filter(status="completed").count()
    return render(request, "barber/sales.html",
                  {"rows": rows, "total": total, "completed": completed})


@barber_required
def barber_new(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")

        errors = []
        if not name:
            errors.append("Name is required.")
        if not EMAIL_RE.match(email):
            errors.append("A valid email is required.")
        elif User.objects.filter(email=email).exists():
            errors.append("That email is already in use.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "barber/barber_form.html",
                          {"form": {"name": name, "email": email,
                                    "phone": phone}})

        User.objects.create_user(email=email, password=password, name=name,
                                 phone=phone, role="barber")
        messages.success(request, f"Barber account created for {name}.")
        return redirect("barber_dashboard")

    return render(request, "barber/barber_form.html", {"form": {}})


@barber_required
def profile(request):
    if request.method == "POST":
        apply_account_update(request)  # validates, persists + flashes
        return redirect("barber_profile")

    return render(request, "barber/profile.html", {})
