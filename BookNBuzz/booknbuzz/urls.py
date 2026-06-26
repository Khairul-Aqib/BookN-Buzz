"""
booknbuzz/urls.py - project URL configuration.

The landing page redirects to the customer home; everything else lives in the
bookings app's URLconf. The Django admin is enabled for convenience.
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="customer_home", permanent=False)),
    path("", include("bookings.urls")),
]
