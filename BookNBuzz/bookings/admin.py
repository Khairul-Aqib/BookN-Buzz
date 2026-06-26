"""bookings/admin.py - register the models for Django's admin site."""

from django.contrib import admin

from .models import Availability, Booking, Notification, Service, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role", "phone", "is_staff")
    list_filter = ("role", "is_staff")
    search_fields = ("name", "email")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "price", "active")
    list_filter = ("active",)


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("barber", "weekday", "date", "start_time", "end_time",
                    "is_blocked")
    list_filter = ("is_blocked",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "barber", "service", "mode", "date",
                    "time_slot", "status", "total_price")
    list_filter = ("status", "mode")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read",)
