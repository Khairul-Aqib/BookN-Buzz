"""
bookings/urls.py - URL routes.

Names map one-to-one to the old Flask endpoints (blueprint.endpoint becomes
blueprint_endpoint), e.g. customer.home -> customer_home, barber.bookings ->
barber_bookings. Templates reference these via {% url %}.
"""

from django.urls import path

from . import views

urlpatterns = [
    # ---- Auth ----
    path("register", views.register, name="auth_register"),
    path("login", views.login_view, name="auth_login"),
    path("logout", views.logout_view, name="auth_logout"),

    # ---- Customer ----
    path("home", views.home, name="customer_home"),
    path("packages", views.packages, name="customer_packages"),
    path("packages/<int:service_id>", views.service_detail,
         name="customer_service_detail"),
    path("book/<int:service_id>", views.book, name="customer_book"),
    path("book/<int:service_id>/barber/<int:barber_id>", views.book_times,
         name="customer_book_times"),
    path("book/<int:service_id>/slots", views.book_slots,
         name="customer_book_slots"),
    path("book/<int:service_id>/confirm", views.confirm_booking,
         name="customer_confirm_booking"),
    path("my-bookings", views.my_bookings, name="customer_my_bookings"),
    path("my-bookings/<int:booking_id>/cancel", views.cancel_booking,
         name="customer_cancel_booking"),
    path("notifications", views.notifications, name="customer_notifications"),
    path("account", views.account, name="customer_account"),

    # ---- Barber ----
    path("barber/dashboard", views.dashboard, name="barber_dashboard"),
    path("barber/customers", views.customers, name="barber_customers"),
    path("barber/services", views.services, name="barber_services"),
    path("barber/services/new", views.service_new, name="barber_service_new"),
    path("barber/services/<int:service_id>/edit", views.service_edit,
         name="barber_service_edit"),
    path("barber/services/<int:service_id>/delete", views.service_delete,
         name="barber_service_delete"),
    path("barber/sales", views.sales, name="barber_sales"),
    path("barber/barbers/new", views.barber_new, name="barber_barber_new"),
    path("barber/profile", views.profile, name="barber_profile"),
    path("barber/availability", views.availability, name="barber_availability"),
    path("barber/availability/weekday", views.set_weekday,
         name="barber_set_weekday"),
    path("barber/availability/block-toggle", views.toggle_block,
         name="barber_toggle_block"),
    path("barber/bookings", views.bookings, name="barber_bookings"),
    path("barber/bookings/<int:booking_id>/confirm", views.barber_confirm_booking,
         name="barber_confirm_booking"),
    path("barber/bookings/<int:booking_id>/claim", views.claim_booking,
         name="barber_claim_booking"),
    path("barber/bookings/<int:booking_id>/release", views.release_booking,
         name="barber_release_booking"),
    path("barber/bookings/<int:booking_id>/status", views.update_status,
         name="barber_update_status"),
]
