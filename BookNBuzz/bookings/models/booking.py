"""Booking - associates Customer + Barber + Service, plus the mobile fee."""

from datetime import date as date_cls

from django.conf import settings
from django.db import models
from django.db.models import Count, Q, Sum

from .service import Service


# Flat surcharge added to a booking when the barber travels to the customer
# (mobile mode). Walk-in bookings have no fee. Defined here ONCE so every layer
# - booking confirm, the booking summary, seed data - uses the same value and
# it can be changed in a single place.
MOBILE_SERVICE_FEE = 25.0


class Booking(models.Model):
    STATUSES = ("pending", "confirmed", "completed", "cancelled")
    MODE_CHOICES = [("walk_in", "Walk-in"), ("mobile", "Mobile")]
    STATUS_CHOICES = [(s, s.title()) for s in STATUSES]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL,
                                 on_delete=models.CASCADE,
                                 related_name="bookings_made")
    barber = models.ForeignKey(settings.AUTH_USER_MODEL,
                               on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="bookings_taken")
    service = models.ForeignKey(Service, on_delete=models.CASCADE,
                                related_name="bookings")
    mode = models.CharField(max_length=10, choices=MODE_CHOICES,
                            default="walk_in")
    date = models.DateField()
    time_slot = models.CharField(max_length=5)  # 'HH:MM'
    service_address = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default="pending")
    total_price = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "bookings"
        db_table = "bookings"
        constraints = [
            # Guard against double-booking the SAME barber for the same
            # date + slot. Cancelled bookings free the slot. SQLite treats NULL
            # barber rows as distinct, so legacy unclaimed rows aren't limited.
            models.UniqueConstraint(
                fields=["barber", "date", "time_slot"],
                condition=~Q(status="cancelled"),
                name="idx_no_double_booking",
            ),
        ]

    # ---- flat accessors so templates can read joined names ----------------
    @property
    def service_name(self):
        return self.service.name

    @property
    def duration_minutes(self):
        return self.service.duration_minutes

    @property
    def customer_name(self):
        return self.customer.name

    @property
    def customer_email(self):
        return self.customer.email

    @property
    def customer_phone(self):
        return self.customer.phone

    @property
    def barber_name(self):
        return self.barber.name if self.barber_id else None

    # ---- pricing -----------------------------------------------------------
    @staticmethod
    def mobile_fee(mode):
        """RM25 surcharge for mobile, nothing for walk-in (single constant)."""
        return MOBILE_SERVICE_FEE if mode == "mobile" else 0.0

    @classmethod
    def compute_total(cls, service_price, mode):
        """Authoritative total = package price + any mobile fee. Always used
        server-side on confirm so the client total is never trusted."""
        return float(service_price) + cls.mobile_fee(mode)

    # ---- creation guard ----------------------------------------------------
    @classmethod
    def is_slot_free(cls, barber, on_date, time_slot):
        """True if THIS barber has no non-cancelled booking at this date+slot."""
        return not (cls.objects.filter(barber=barber, date=on_date,
                                       time_slot=time_slot)
                    .exclude(status="cancelled").exists())

    # ---- queries -----------------------------------------------------------
    @classmethod
    def _base(cls):
        return cls.objects.select_related("service", "customer", "barber")

    @classmethod
    def for_customer(cls, customer):
        return cls._base().filter(customer=customer).order_by("-date",
                                                              "time_slot")

    @classmethod
    def for_date(cls, on_date, status=None):
        """All bookings on a date shop-wide; unclaimed sort to the top."""
        qs = cls._base().filter(date=on_date)
        if status:
            qs = qs.filter(status=status)
        return qs.annotate(
            has_barber=models.Case(
                models.When(barber__isnull=True, then=0),
                default=1, output_field=models.IntegerField())
        ).order_by("has_barber", "-date", "time_slot")

    @classmethod
    def for_day(cls, on_date, status=None):
        """Bookings on a single date, earliest time first (per-date view)."""
        qs = cls._base().filter(date=on_date)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("time_slot")

    @classmethod
    def pending_all(cls):
        """Every pending / unclaimed booking across all dates (soonest first)."""
        return (cls._base().filter(Q(status="pending") | Q(barber__isnull=True))
                .order_by("date", "time_slot"))

    @classmethod
    def pending_count(cls):
        return cls.objects.filter(Q(status="pending") |
                                  Q(barber__isnull=True)).count()

    @classmethod
    def counts_by_date(cls):
        """Map of ISO date -> number of active (non-cancelled) bookings, for the
        calendar's busy-day dots."""
        rows = (cls.objects.exclude(status="cancelled")
                .values("date").annotate(c=Count("id")))
        return {r["date"].isoformat(): r["c"] for r in rows}

    # ---- confirm / claim / release ----------------------------------------
    @classmethod
    def confirm(cls, booking_id, barber):
        """Confirm a pending booking already assigned to this barber."""
        cls.objects.filter(id=booking_id, barber=barber,
                           status="pending").update(status="confirmed")
        return cls.objects.filter(id=booking_id, barber=barber,
                                  status="confirmed").exists()

    @classmethod
    def claim(cls, booking_id, barber):
        """Claim an unclaimed pending booking: assign the barber AND confirm it."""
        cls.objects.filter(id=booking_id, barber__isnull=True,
                           status="pending").update(barber=barber,
                                                    status="confirmed")
        return cls.objects.filter(id=booking_id, barber=barber).exists()

    @classmethod
    def release(cls, booking_id, barber):
        """Release a confirmed booking back to the pool: unclaim AND set pending."""
        cls.objects.filter(id=booking_id, barber=barber,
                           status="confirmed").update(barber=None,
                                                      status="pending")

    # ---- status changes ----------------------------------------------------
    @classmethod
    def set_status(cls, booking_id, status):
        cls.objects.filter(id=booking_id).update(status=status)

    @classmethod
    def cancel(cls, booking_id, customer):
        """Customer-initiated cancel (only their own, only if not finished)."""
        cls.objects.filter(id=booking_id, customer=customer,
                           status__in=("pending", "confirmed")).update(
                               status="cancelled")

    # ---- sales report ------------------------------------------------------
    @classmethod
    def sales_report(cls):
        """Revenue from completed bookings, grouped by service."""
        completed = cls.objects.filter(status="completed")
        rows = (completed.values(service_name=models.F("service__name"))
                .annotate(sold=Count("id"), revenue=Sum("total_price"))
                .order_by("-revenue"))
        total = completed.aggregate(t=Sum("total_price"))["t"] or 0.0
        return list(rows), total

    # ---- dashboard stats (shop-wide) --------------------------------------
    @classmethod
    def dashboard_stats(cls):
        today = date_cls.today()
        qs = cls.objects
        revenue = (qs.filter(status="completed")
                   .aggregate(s=Sum("total_price"))["s"] or 0.0)
        return {
            "total": qs.count(),
            "pending": qs.filter(status="pending").count(),
            "unclaimed": qs.filter(barber__isnull=True)
                          .exclude(status__in=("cancelled", "completed")).count(),
            "today": qs.filter(date=today).count(),
            "revenue": revenue,
        }
