"""
bookings/decorators.py - access-control helpers.

@login_required (Django's own) protects customer pages; barber_required adds a
role gate so only barbers reach the management area. Mirrors the old
auth_utils.py decorators.
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def barber_required(view):
    """Allow only logged-in barbers; redirect everyone else with a message."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to continue.")
            return redirect("auth_login")
        if request.user.role != "barber":
            messages.error(request, "That area is for barbers only.")
            return redirect("customer_packages")
        return view(request, *args, **kwargs)

    return wrapped
