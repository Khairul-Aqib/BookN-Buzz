"""
bookings/context_processors.py - template globals for the nav bar.

Exposes the logged-in user, the customer's unread-notification count, and the
shared mobile-fee constant to every template (the same trio the old Flask
context processor injected).
"""

from .models import MOBILE_SERVICE_FEE


def nav(request):
    user = request.user if request.user.is_authenticated else None
    unread = 0
    if user is not None and user.role == "customer":
        unread = user.unread_count()
    return {
        "current_user": user,
        "unread_count": unread,
        "mobile_fee": MOBILE_SERVICE_FEE,
    }
