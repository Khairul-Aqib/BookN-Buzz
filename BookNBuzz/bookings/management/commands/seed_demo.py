"""
seed_demo - build demo data for BookN'Buzz.

Run after migrating:  python manage.py seed_demo
Creates three barbers (one also a Django superuser/admin), six customers, the
service menu, weekly availability + blocked days, and a realistic spread of
bookings (past completed for the sales report, a cancelled one, today's
appointments for the dashboard, future pending/confirmed jobs, a mix of walk-in
and mobile so the RM25 mobile fee shows up, plus one legacy unclaimed booking to
demo the Claim flow). Re-running wipes and rebuilds the demo data.
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from bookings.models import (Availability, Booking, Notification, Service, User)


# --------------------------------------------------------------------------- #
#  Demo content
# --------------------------------------------------------------------------- #
SERVICES = [
    ("Classic Cut", "Timeless scissor or clipper cut tailored to your style, "
     "finished with a hot-towel neck shave.", 30, 25.0, "ClassicCut.jpg"),
    ("Skin Fade", "Sharp, blended fade from skin up - the modern signature "
     "look, precision lined.", 45, 32.0, "SkinFade.jpg"),
    ("Beard Sculpt", "Beard trim, shape and line-up with hot towel and "
     "conditioning beard oil.", 30, 18.0, "BeardSculpt.jpg"),
    ("Cut & Beard Combo", "Full haircut paired with a beard sculpt - the "
     "complete grooming package.", 60, 40.0, "FullPackage.jpg"),
    ("Hot Towel Shave", "Traditional straight-razor shave with hot towels, "
     "pre-shave oil and balm.", 30, 22.0, "HotTowelShave.jpg"),
    ("Buzz & Tidy", "Quick all-over clipper cut and neckline tidy - in and "
     "out, fresh and clean.", 20, 15.0, "BuzzTidy.jpg"),
]

# (name, email, phone, working weekdays [0=Mon..6=Sun], open, close)
BARBERS = [
    ("Marcus Reed", "marcus@booknbuzz.com", "03-1234 5670",
     range(0, 6), "09:00", "17:00"),     # Mon-Sat
    ("Theo Blades", "theo@booknbuzz.com", "03-1234 5671",
     range(1, 6), "10:00", "18:00"),     # Tue-Sat
    ("Aisha Khan", "aisha@booknbuzz.com", "03-1234 5672",
     range(0, 5), "11:00", "19:00"),     # Mon-Fri
]

CUSTOMERS = [
    ("Alex Johnson", "alex@example.com", "012-345 6789"),
    ("Sam Carter", "sam@example.com", "012-988 1122"),
    ("Jordan Lee", "jordan@example.com", "013-477 8890"),
    ("Nadia Rahman", "nadia@example.com", "011-2345 6677"),
    ("Wei Jie Tan", "weijie@example.com", "016-700 4521"),
    ("Priya Suresh", "priya@example.com", "017-882 3390"),
]


def _notification_for(status, barber, service_name, on_date, slot):
    """A customer-facing message matching the booking's current status, mirroring
    the wording the live app produces on each transition."""
    who = barber.name if barber else None
    if status == "pending":
        if who:
            return (f"Booking requested with {who}: {service_name} on "
                    f"{on_date} at {slot}. Status is pending confirmation.")
        return (f"Booking requested: {service_name} on {on_date} at {slot}. "
                f"Awaiting a barber to claim it.")
    if status == "confirmed":
        return (f"{who} confirmed your {service_name} booking on {on_date} at "
                f"{slot}. See you then!")
    if status == "completed":
        return (f"Your {service_name} booking on {on_date} at {slot} is now "
                f"COMPLETED. Thanks for visiting BookN'Buzz!")
    if status == "cancelled":
        return (f"Your {service_name} booking on {on_date} at {slot} was "
                f"cancelled.")
    return None


class Command(BaseCommand):
    help = "Wipe and rebuild the BookN'Buzz demo data."

    @transaction.atomic
    def run(self):
        self.stdout.write("Resetting demo data ...")
        # Clear everything the demo owns (cascades handle availability/bookings).
        Notification.objects.all().delete()
        Booking.objects.all().delete()
        Availability.objects.all().delete()
        Service.objects.all().delete()
        User.objects.all().delete()

        # --- Barbers / admins ------------------------------------------------
        barbers = []
        for i, (name, email, phone, weekdays, start, end) in enumerate(BARBERS):
            b = User.objects.create_user(email=email, password="barber123",
                                         name=name, phone=phone, role="barber")
            if i == 0:
                # First barber doubles as the Django admin superuser.
                b.is_staff = True
                b.is_superuser = True
                b.save(update_fields=["is_staff", "is_superuser"])
            for weekday in weekdays:
                Availability.objects.create(barber=b, weekday=weekday, date=None,
                                            start_time=start, end_time=end,
                                            is_blocked=False)
            barbers.append(b)
        marcus, theo, aisha = barbers
        self.stdout.write(
            f"  barbers: {', '.join(b.email for b in barbers)} (barber123)")

        # --- Customers -------------------------------------------------------
        customers = []
        for name, email, phone in CUSTOMERS:
            c = User.objects.create_user(email=email, password="password123",
                                         name=name, phone=phone, role="customer")
            customers.append(c)
        self.stdout.write(f"  customers: {len(customers)} created (password123)")

        # --- Services --------------------------------------------------------
        services = []
        for name, desc, dur, price, img in SERVICES:
            s = Service.objects.create(name=name, description=desc,
                                       duration_minutes=dur, price=price,
                                       image=img, active=True)
            services.append(s)
        self.stdout.write(f"  services: {len(services)} created")

        # --- Blocked days (each on a day the barber actually works) ----------
        today = date.today()

        def block_a_workday(barber, weekdays, offset):
            d = today + timedelta(days=offset)
            allowed = set(weekdays)
            while d.weekday() not in allowed:
                d += timedelta(days=1)
            Availability.objects.create(barber=barber, weekday=None, date=d,
                                        start_time="00:00", end_time="23:59",
                                        is_blocked=True)
            return d

        block_a_workday(marcus, range(0, 6), 8)   # Marcus off ~next week
        block_a_workday(theo, range(1, 6), 9)     # Theo off ~next week

        # --- Bookings --------------------------------------------------------
        used = set()

        def add_minutes(hhmm, mins):
            h, m = map(int, hhmm.split(":"))
            total = h * 60 + m + mins
            return f"{total // 60:02d}:{total % 60:02d}"

        def book(cust, svc, mode, day_offset, slot, barber, status,
                 address=None):
            iso = today + timedelta(days=day_offset)
            if status != "cancelled" and barber is not None:
                while (barber.id, iso, slot) in used:
                    slot = add_minutes(slot, 30)
                used.add((barber.id, iso, slot))
            Booking.objects.create(
                customer=cust, barber=barber, service=svc, mode=mode, date=iso,
                time_slot=slot, service_address=address, status=status,
                total_price=Booking.compute_total(svc.price, mode))
            msg = _notification_for(status, barber, svc.name, iso.isoformat(),
                                    slot)
            if msg:
                Notification.push(cust, msg)

        # Welcome note first so it keeps the lowest id and stays at the bottom
        # of each customer's list (newest booking updates appear above it).
        for cust in customers:
            Notification.push(cust, "Welcome to BookN'Buzz! Book your next "
                                    "fresh cut in seconds.")

        c = customers  # shorthand
        # (cust, service, mode, day_offset, slot, barber, status[, address])
        BOOKINGS = [
            # ---- Past: completed (feeds the sales report across services) ----
            (c[0], services[0], "walk_in", -2, "10:00", marcus, "completed"),
            (c[1], services[1], "walk_in", -3, "11:00", theo, "completed"),
            (c[2], services[3], "mobile", -3, "14:00", marcus, "completed",
             "42 Oak Street, Apt 5"),
            (c[3], services[2], "walk_in", -5, "12:30", aisha, "completed"),
            (c[4], services[4], "walk_in", -6, "15:00", theo, "completed"),
            (c[5], services[5], "mobile", -7, "16:00", aisha, "completed",
             "7 Pine Avenue"),
            (c[0], services[1], "walk_in", -8, "09:30", marcus, "completed"),
            (c[1], services[0], "walk_in", -9, "13:00", theo, "completed"),
            (c[2], services[4], "mobile", -10, "11:30", marcus, "completed",
             "18 Maple Court"),

            # ---- Past: cancelled --------------------------------------------
            (c[3], services[0], "walk_in", -4, "10:30", theo, "cancelled"),

            # ---- Today: dashboard mix ---------------------------------------
            (c[0], services[0], "walk_in", 0, "10:00", marcus, "confirmed"),
            (c[1], services[1], "mobile", 0, "11:30", theo, "confirmed",
             "12 Jalan Bukit, Unit 3"),
            (c[4], services[2], "walk_in", 0, "14:00", marcus, "pending"),
            (c[2], services[5], "walk_in", 0, "12:00", aisha, "confirmed"),

            # ---- Future: pending + confirmed --------------------------------
            (c[3], services[3], "mobile", 1, "15:00", theo, "pending",
             "88 Riverside Walk"),
            (c[5], services[0], "walk_in", 2, "10:00", marcus, "confirmed"),
            (c[0], services[4], "walk_in", 2, "16:30", theo, "pending"),
            (c[1], services[1], "mobile", 3, "13:30", aisha, "confirmed",
             "5 Garden Terrace"),

            # ---- Future: legacy unclaimed (no barber -> Claim demo) ---------
            (c[4], services[2], "mobile", 3, "14:00", None, "pending",
             "23 Hillcrest Road"),
        ]
        for entry in BOOKINGS:
            book(*entry)
        self.stdout.write(f"  bookings: {len(BOOKINGS)} created "
                          f"(completed/cancelled/today/future + 1 unclaimed)")

        self.stdout.write(self.style.SUCCESS("\nDone. Start the app with:  "
                                             "python manage.py runserver"))
        self.stdout.write("Then open http://localhost:8000\n")
        self.stdout.write("Demo logins")
        self.stdout.write("  Barber/admin : marcus@booknbuzz.com / barber123")
        self.stdout.write("  Customer     : alex@example.com / password123")

    def handle(self, *args, **options):
        self.run()
