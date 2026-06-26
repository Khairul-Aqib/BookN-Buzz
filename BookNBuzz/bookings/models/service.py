"""Service - a haircut / beard / grooming package."""

from django.db import models


class Service(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.IntegerField(default=30)
    price = models.FloatField(default=0.0)
    image = models.CharField(max_length=255, blank=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        app_label = "bookings"
        db_table = "services"
        ordering = ["name"]

    def __str__(self):
        return self.name
