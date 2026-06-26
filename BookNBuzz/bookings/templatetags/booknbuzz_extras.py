"""
bookings/templatetags/booknbuzz_extras.py - small template helpers.

`money`  - pretty currency, e.g. 25 -> "RM25.00" (was a Flask template filter).
`tojson` - JSON-encode a value for a data-* attribute (was Jinja's |tojson).
"""

import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def money(value):
    try:
        return f"RM{float(value):.2f}"
    except (TypeError, ValueError):
        return "RM0.00"


@register.filter(is_safe=True)
def tojson(value):
    return mark_safe(json.dumps(value))
