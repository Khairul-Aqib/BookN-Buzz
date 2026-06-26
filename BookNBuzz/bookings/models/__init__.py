"""
bookings.models - the MODEL layer (Django ORM), split one file per entity.

Importing order matters: User and Service have no model dependencies, Booking
references Service, and Availability references Booking. Everything is
re-exported here so the rest of the app keeps importing
`from bookings.models import User, Service, ...` unchanged.
"""

from .user import User, UserManager
from .service import Service
from .booking import Booking, MOBILE_SERVICE_FEE
from .availability import Availability
from .notification import Notification

__all__ = [
    "User", "UserManager", "Service", "Booking", "MOBILE_SERVICE_FEE",
    "Availability", "Notification",
]
