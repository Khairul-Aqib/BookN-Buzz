"""
seed.py - build the database and load demo data.

Run once before starting the app:  python seed.py
Creates the schema, three barbers, six customers, the service menu, and a
realistic spread of bookings (past completed for the sales report, a cancelled
one, today's appointments for the dashboard, future pending/confirmed jobs, a
mix of walk-in and mobile so the RM25 mobile fee shows up, plus one legacy
unclaimed booking to demo the Claim flow). Re-running wipes and rebuilds the DB.
"""

from datetime import date, timedelta

import db
from app import create_app
from model import (Barber, Customer, Service, Booking, Availability,
                   Notification)


# --------------------------------------------------------------------------- #
#  Demo content
# --------------------------------------------------------------------------- #
SERVICES = [
    ("Classic Cut", "Timeless scissor or clipper cut tailored to your style, "
     "finished with a hot-towel neck shave.", 30, 25.0, "classic-cut.svg"),
    ("Skin Fade", "Sharp, blended fade from skin up - the modern signature "
     "look, precision lined.", 45, 32.0, "skin-fade.svg"),
    ("Beard Sculpt", "Beard trim, shape and line-up with hot towel and "
     "conditioning beard oil.", 30, 18.0, "beard-sculpt.svg"),
    ("Cut & Beard Combo", "Full haircut paired with a beard sculpt - the "
     "complete grooming package.", 60, 40.0, "cut-beard-combo.svg"),
    ("Hot Towel Shave", "Traditional straight-razor shave with hot towels, "
     "pre-shave oil and balm.", 30, 22.0, "hot-towel-shave.svg"),
    ("Buzz & Tidy", "Quick all-over clipper cut and neckline tidy - in and "
     "out, fresh and clean.", 20, 15.0, "buzz-tidy.svg"),
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


def run():
    app = create_app()
    with app.app_context():
        print("Resetting database ...")
        db.reset_db()
        db.init_db()

        # --- Barbers / admins ------------------------------------------------
        barbers = []
        for name, email, phone, weekdays, start, end in BARBERS:
            b = Barber(name=name, email=email, phone=phone)
            b.set_password("barber123")
            b.save()
            for weekday in weekdays:
                Availability(barber_id=b.id, weekday=weekday, date=None,
                             start_time=start, end_time=end,
                             is_blocked=0).save()
            barbers.append(b)
        marcus, theo, aisha = barbers
        print(f"  barbers: {', '.join(b.email for b in barbers)} (barber123)")

        # --- Customers -------------------------------------------------------
        customers = []
        for name, email, phone in CUSTOMERS:
            c = Customer(name=name, email=email, phone=phone)
            c.set_password("password123")
            c.save()
            customers.append(c)
        print(f"  customers: {len(customers)} created (password123)")

        # --- Services --------------------------------------------------------
        services = []
        for name, desc, dur, price, img in SERVICES:
            s = Service(name=name, description=desc, duration_minutes=dur,
                        price=price, image=img, active=1)
            s.save()
            services.append(s)
        print(f"  services: {len(services)} created")

        # --- Blocked days (each on a day the barber actually works) ----------
        today = date.today()

        def block_a_workday(barber, weekdays, offset):
            d = today + timedelta(days=offset)
            allowed = set(weekdays)
            while d.weekday() not in allowed:
                d += timedelta(days=1)
            Availability(barber_id=barber.id, weekday=None,
                         date=d.isoformat(), start_time="00:00",
                         end_time="23:59", is_blocked=1).save()
            return d

        block_a_workday(marcus, range(0, 6), 8)   # Marcus off ~next week
        block_a_workday(theo, range(1, 6), 9)     # Theo off ~next week

        # --- Bookings --------------------------------------------------------
        # Slots are kept unique per (barber, date) so the no-double-booking
        # index is never violated; a tiny guard nudges any clash forward.
        used = set()

        def add_minutes(hhmm, mins):
            h, m = map(int, hhmm.split(":"))
            total = h * 60 + m + mins
            return f"{total // 60:02d}:{total % 60:02d}"

        def book(cust, svc, mode, day_offset, slot, barber, status,
                 address=None):
            iso = (today + timedelta(days=day_offset)).isoformat()
            bid = barber.id if barber else None
            if status != "cancelled" and bid is not None:
                while (bid, iso, slot) in used:
                    slot = add_minutes(slot, 30)
                used.add((bid, iso, slot))
            Booking(customer_id=cust.id, barber_id=bid, service_id=svc.id,
                    mode=mode, date=iso, time_slot=slot,
                    service_address=address, status=status,
                    total_price=Booking.compute_total(svc.price, mode)).save()
            msg = _notification_for(status, barber, svc.name, iso, slot)
            if msg:
                Notification.push(cust.id, msg)

        # Welcome note first so it keeps the lowest id and stays at the bottom
        # of each customer's list (newest booking updates appear above it).
        for cust in customers:
            Notification.push(cust.id, "Welcome to BookN'Buzz! Book your next "
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
        print(f"  bookings: {len(BOOKINGS)} created "
              f"(completed/cancelled/today/future + 1 unclaimed)")

        print("\nDone. Start the app with:  python app.py")
        print("Then open http://localhost:5000\n")
        print("Demo logins")
        print("  Barber/admin : marcus@booknbuzz.com / barber123")
        print("  Customer     : alex@example.com / password123")


if __name__ == "__main__":
    run()
