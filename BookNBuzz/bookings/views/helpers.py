"""
bookings.views.helpers - helpers and constants shared by the user and barber
view modules (date parsing, lookups, the email regex, weekday labels).
"""

import re
from datetime import date as date_cls

from django.http import Http404

from bookings.models import Service, User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]


def active_service_or_404(service_id):
    try:
        service = Service.objects.get(pk=service_id)
    except Service.DoesNotExist:
        raise Http404
    if not service.active:
        raise Http404
    return service


def get_barber(barber_id):
    if barber_id is None:
        return None
    try:
        return User.objects.get(pk=barber_id, role="barber")
    except User.DoesNotExist:
        return None


def pretty_date(d):
    """date object -> 'Thu, 25 June' (empty string for None)."""
    if not d:
        return ""
    # %-d isn't portable (Windows), so build the day number by hand.
    return d.strftime("%a, ") + str(d.day) + d.strftime(" %B")


def parse_iso(value):
    try:
        return date_cls.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def back(request, fallback):
    """The referring page, or a fallback URL (for post-action redirects)."""
    return request.META.get("HTTP_REFERER") or fallback
