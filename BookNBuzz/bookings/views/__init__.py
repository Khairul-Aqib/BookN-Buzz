"""
bookings.views - the VIEW layer, grouped by audience:

    views/user/    -> auth + customer-facing use cases
    views/barber/  -> barber/admin management area
    views/helpers.py -> helpers shared by both

Everything is re-exported here so the URLconf can keep referring to
`views.<name>` regardless of which role module a view lives in.
"""

from .user import (account, book, book_slots, book_times, cancel_booking,
                   confirm_booking, home, login_view, logout_view, my_bookings,
                   notifications, packages, register, service_detail)
from .barber import (availability, barber_confirm_booking, barber_new, bookings,
                     claim_booking, customers, dashboard, profile,
                     release_booking, sales, service_delete, service_edit,
                     service_new, services, set_weekday, toggle_block,
                     update_status)

__all__ = [
    # user / auth
    "register", "login_view", "logout_view",
    "home", "packages", "service_detail", "book", "book_times", "book_slots",
    "confirm_booking", "my_bookings", "cancel_booking", "notifications",
    "account",
    # barber
    "dashboard", "customers", "sales", "barber_new", "profile",
    "services", "service_new", "service_edit", "service_delete",
    "availability", "set_weekday", "toggle_block",
    "bookings", "barber_confirm_booking", "claim_booking", "release_booking",
    "update_status",
]
