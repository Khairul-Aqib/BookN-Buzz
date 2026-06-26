"""
bookings.views.barber - the BARBER (management/admin) area of the View layer:
dashboard, customers, sales, services CRUD, availability, bookings management
and the barber's own profile / account creation.
"""

from .dashboard_views import barber_new, customers, dashboard, profile, sales
from .service_views import (service_delete, service_edit, service_new, services)
from .availability_views import availability, set_weekday, toggle_block
from .booking_views import (barber_confirm_booking, bookings, claim_booking,
                            release_booking, update_status)

__all__ = [
    "dashboard", "customers", "sales", "barber_new", "profile",
    "services", "service_new", "service_edit", "service_delete",
    "availability", "set_weekday", "toggle_block",
    "bookings", "barber_confirm_booking", "claim_booking", "release_booking",
    "update_status",
]
