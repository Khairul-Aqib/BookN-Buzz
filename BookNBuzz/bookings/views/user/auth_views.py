"""
User area - authentication: Register, Login, Logout.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from bookings.models import User
from bookings.views.helpers import EMAIL_RE


def register(request):
    if request.user.is_authenticated:
        return redirect("customer_home")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm", "")

        errors = []
        if not name:
            errors.append("Please enter your name.")
        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")
        elif User.objects.filter(email=email).exists():
            errors.append("That email is already registered. Try logging in.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "auth/register.html",
                          {"form": {"name": name, "email": email,
                                    "phone": phone}})

        user = User.objects.create_user(email=email, password=password,
                                        name=name, phone=phone,
                                        role="customer")
        login(request, user)
        messages.success(request,
                         f"Welcome to BookN'Buzz, {name}! Your account is ready.")
        return redirect("customer_home")

    return render(request, "auth/register.html", {"form": {}})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("customer_home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
            return render(request, "auth/login.html", {"form": {"email": email}})

        login(request, user)
        messages.success(request, f"Welcome back, {user.name}!")
        if user.role == "barber":
            return redirect("barber_dashboard")
        return redirect("customer_home")

    return render(request, "auth/login.html", {"form": {}})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("auth_login")
