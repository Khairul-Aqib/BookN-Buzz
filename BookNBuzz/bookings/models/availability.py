"""Availability - a barber's working hours / blocked days + slot generation."""

from datetime import datetime, timedelta

from django.conf import settings
from django.db import models

from .booking import Booking


class Availability(models.Model):
    """A row is either a recurring weekly block (weekday set, date NULL) or a
    specific-date entry. is_blocked marks a day the barber is unavailable."""

    SLOT_MINUTES = 30  # granularity of generated time slots

    barber = models.ForeignKey(settings.AUTH_USER_MODEL,
                               on_delete=models.CASCADE,
                               related_name="availabilities")
    weekday = models.IntegerField(null=True, blank=True)  # 0=Mon..6=Sun
    date = models.DateField(null=True, blank=True)        # specific date
    start_time = models.CharField(max_length=5)           # 'HH:MM'
    end_time = models.CharField(max_length=5)             # 'HH:MM'
    is_blocked = models.BooleanField(default=False)

    class Meta:
        app_label = "bookings"
        db_table = "availability"
        ordering = ["is_blocked", "weekday", "date", "start_time"]

    # ---- read helpers ------------------------------------------------------
    @classmethod
    def blocked_dates(cls, barber):
        """ISO date strings the barber has blocked off (for the calendar UI)."""
        rows = (cls.objects.filter(barber=barber, is_blocked=True,
                                   date__isnull=False)
                .values_list("date", flat=True).distinct())
        return [d.isoformat() for d in rows]

    @classmethod
    def working_weekdays(cls, barber):
        """Weekdays (0=Mon..6=Sun) the barber has working hours on."""
        rows = (cls.objects.filter(barber=barber, is_blocked=False,
                                   weekday__isnull=False)
                .values_list("weekday", flat=True).distinct())
        return sorted(set(rows))

    @classmethod
    def is_blocked_date(cls, barber, on_date):
        """True if the barber blocked this exact date (server-side guard)."""
        return cls.objects.filter(barber=barber, date=on_date,
                                  is_blocked=True).exists()

    @classmethod
    def weekly_schedule(cls, barber):
        """List of 7 dicts (Mon..Sun) describing the working week.

        Each dict: {weekday, open, start, end}. Days with no hours come back as
        closed with sensible default times pre-filled for when they're opened.
        """
        rows = cls.objects.filter(barber=barber, is_blocked=False,
                                  weekday__isnull=False, date__isnull=True)
        by_day = {}
        for r in rows:
            by_day.setdefault(r.weekday, (r.start_time, r.end_time))

        schedule = []
        for wd in range(7):
            if wd in by_day:
                start, end = by_day[wd]
                schedule.append({"weekday": wd, "open": True,
                                 "start": start, "end": end})
            else:
                schedule.append({"weekday": wd, "open": False,
                                 "start": "09:00", "end": "17:00"})
        return schedule

    # ---- weekly schedule editing ------------------------------------------
    @classmethod
    def clear_weekday(cls, barber, weekday):
        """Remove the recurring working hours for a weekday (closes the day)."""
        cls.objects.filter(barber=barber, weekday=weekday,
                           is_blocked=False, date__isnull=True).delete()

    @classmethod
    def set_weekday(cls, barber, weekday, start, end):
        """Replace a weekday's working hours with a single window."""
        cls.clear_weekday(barber, weekday)
        cls.objects.create(barber=barber, weekday=weekday, date=None,
                           start_time=start, end_time=end, is_blocked=False)

    @classmethod
    def toggle_block(cls, barber, on_date):
        """Block the date if free, or unblock it if already blocked.

        Returns True if the date is now blocked, False if now unblocked.
        """
        existing = cls.objects.filter(barber=barber, date=on_date,
                                      is_blocked=True)
        if existing.exists():
            existing.delete()
            return False
        cls.objects.create(barber=barber, weekday=None, date=on_date,
                           start_time="00:00", end_time="23:59",
                           is_blocked=True)
        return True

    # ---- the core scheduling logic ----------------------------------------
    @staticmethod
    def _to_minutes(hhmm):
        """'HH:MM' -> minutes since midnight (None if unparseable)."""
        try:
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)
        except (ValueError, AttributeError):
            return None

    @classmethod
    def booked_intervals(cls, barber, on_date):
        """[(start_min, end_min)] for this barber's active bookings on a date.

        Each booking occupies its slot start through start + service duration,
        so a 60-min service blocks the slots it overlaps - not just its start.
        """
        rows = (Booking.objects.filter(barber=barber, date=on_date)
                .exclude(status="cancelled")
                .values_list("time_slot", "service__duration_minutes"))
        intervals = []
        for time_slot, duration in rows:
            start = cls._to_minutes(time_slot)
            if start is None:
                continue
            intervals.append((start, start + int(duration or 0)))
        return intervals

    @classmethod
    def open_slots(cls, barber, on_date, duration_minutes=30):
        """Free 'HH:MM' slots for THIS barber on a date (a date object).

        A slot is offered only when it (a) falls inside the barber's working
        hours for that weekday, (b) is not on one of the barber's blocked days,
        (c) leaves room for the full service before closing time, and (d) does
        not overlap a booking that barber already has. Past slots for today are
        also hidden.
        """
        if on_date is None:
            return []

        weekday = on_date.weekday()  # Monday = 0

        # Whole-day block for this exact date?
        if cls.objects.filter(barber=barber, date=on_date,
                              is_blocked=True).exists():
            return []

        # Working-hour windows: recurring weekly rows for this weekday.
        windows = (cls.objects.filter(barber=barber, is_blocked=False,
                                      weekday=weekday, date__isnull=True)
                   .order_by("start_time")
                   .values_list("start_time", "end_time"))
        if not windows:
            return []

        # This barber's existing bookings (as minute intervals) for the date.
        busy = cls.booked_intervals(barber, on_date)

        now = datetime.now()
        slots = []
        for start_time, end_time in windows:
            cursor = datetime.strptime(start_time, "%H:%M")
            end = datetime.strptime(end_time, "%H:%M")
            # Last start time that still leaves room for the service.
            while cursor + timedelta(minutes=duration_minutes) <= end:
                label = cursor.strftime("%H:%M")
                slot_start = cursor.hour * 60 + cursor.minute
                slot_end = slot_start + duration_minutes
                overlaps = any(slot_start < b_end and b_start < slot_end
                               for b_start, b_end in busy)
                slot_dt = datetime.combine(on_date, cursor.time())
                if not overlaps and slot_dt > now:
                    slots.append(label)
                cursor += timedelta(minutes=cls.SLOT_MINUTES)
        return sorted(set(slots))
