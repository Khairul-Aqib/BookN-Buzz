"""
bookings.views.user - the USER (customer-facing) area of the View layer:
authentication plus everything a customer does (browse, book, manage bookings,
notifications, account).
"""

from .auth_views import register, login_view, logout_view
from .customer_views import (account, book, book_slots, book_times,
                             cancel_booking, confirm_booking, home, my_bookings,
                             notifications, packages, service_detail)

__all__ = [
    "register", "login_view", "logout_view",
    "home", "packages", "service_detail", "book", "book_times", "book_slots",
    "confirm_booking", "my_bookings", "cancel_booking", "notifications",
    "account",
]
