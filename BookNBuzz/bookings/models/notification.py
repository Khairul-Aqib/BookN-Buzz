"""Notification - a message belonging to a User."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "bookings"
        db_table = "notifications"
        ordering = ["-created_at", "-id"]

    @classmethod
    def push(cls, user, message):
        """Create a notification for a user (called on status changes etc.)."""
        return cls.objects.create(user=user, message=message)

    @classmethod
    def for_user(cls, user):
        return cls.objects.filter(user=user).order_by("-created_at", "-id")

    @classmethod
    def unread_count(cls, user):
        return cls.objects.filter(user=user, is_read=False).count()

    @classmethod
    def mark_all_read(cls, user):
        cls.objects.filter(user=user).update(is_read=True)
