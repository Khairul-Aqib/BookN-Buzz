"""
seed.py - build the database and load demo data.

Run once before starting the app:  python seed.py
Creates the schema, a demo barber/admin, a few customers, ~5 services and some
sample bookings + notifications.  Re-running wipes and rebuilds the DB.
"""

from datetime import date, timedelta

import db
from app import create_app
from model import Barber, Customer, Service, Booking, Availability, Notification


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

CUSTOMERS = [
    ("Alex Johnson", "alex@example.com", "555-0101"),
    ("Sam Carter", "sam@example.com", "555-0102"),
    ("Jordan Lee", "jordan@example.com", "555-0103"),
]


def run():
    app = create_app()
    with app.app_context():
        print("Resetting database ...")
        db.reset_db()
        db.init_db()

        # --- Barber / admin --------------------------------------------------
        barber = Barber(name="Marcus the Barber", email="barber@booknbuzz.com",
                        phone="555-0001")
        barber.set_password("barber123")
        barber.save()
        print(f"  barber: {barber.email} / barber123")

        # A second barber to show "Create Barber Account" worked.
        b2 = Barber(name="Theo Blades", email="theo@booknbuzz.com",
                    phone="555-0002")
        b2.set_password("barber123")
        b2.save()

        # --- Customers -------------------------------------------------------
        customers = []
        for name, email, phone in CUSTOMERS:
            c = Customer(name=name, email=email, phone=phone)
            c.set_password("password123")
            c.save()
            customers.append(c)
        print(f"  customers: {', '.join(c.email for c in customers)} "
              f"(password123)")

        # --- Services --------------------------------------------------------
        services = []
        for name, desc, dur, price, img in SERVICES:
            s = Service(name=name, description=desc, duration_minutes=dur,
                        price=price, image=img, active=1)
            s.save()
            services.append(s)
        print(f"  services: {len(services)} created")

        # --- Availability: Mon-Sat, 09:00-17:00 for the main barber ----------
        for weekday in range(0, 6):  # Monday..Saturday
            Availability(barber_id=barber.id, weekday=weekday, date=None,
                         start_time="09:00", end_time="17:00",
                         is_blocked=0).save()
        # Block next Sunday as an example.
        days_to_sunday = (6 - date.today().weekday()) % 7
        next_sunday = date.today() + timedelta(days=days_to_sunday or 7)
        Availability(barber_id=barber.id, weekday=None,
                     date=next_sunday.isoformat(), start_time="00:00",
                     end_time="23:59", is_blocked=1).save()

        # --- Sample bookings -------------------------------------------------
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        # who_claims: a Barber object = claimed by them, None = unclaimed (N/A).
        samples = [
            # (customer, service, mode, date, slot, address, status, who_claims)
            (customers[0], services[0], "walk_in", today.isoformat(),
             "10:00", None, "confirmed", barber),       # Marcus
            (customers[1], services[1], "walk_in", today.isoformat(),
             "11:30", None, "pending", None),            # unclaimed / N/A
            (customers[2], services[3], "mobile", tomorrow.isoformat(),
             "14:00", "42 Oak Street, Apt 5", "pending", None),   # unclaimed
            (customers[0], services[4], "walk_in", yesterday.isoformat(),
             "09:30", None, "completed", barber),        # Marcus
            (customers[1], services[2], "walk_in", yesterday.isoformat(),
             "15:00", None, "completed", b2),            # Theo
            (customers[2], services[5], "mobile", yesterday.isoformat(),
             "13:00", "7 Pine Avenue", "completed", b2), # Theo
        ]
        for cust, svc, mode, d, slot, addr, status, who in samples:
            Booking(customer_id=cust.id,
                    barber_id=(who.id if who else None),
                    service_id=svc.id, mode=mode, date=d, time_slot=slot,
                    service_address=addr, status=status,
                    total_price=svc.price).save()
        print(f"  bookings: {len(samples)} created "
              f"(2 unclaimed/N/A, ready to be claimed)")

        # --- A welcome notification per customer -----------------------------
        for c in customers:
            Notification.push(c.id, "Welcome to BookN'Buzz! Book your first "
                                    "fresh cut today.")

        print("\nDone. Start the app with:  python app.py")
        print("Then open http://localhost:5000\n")
        print("Demo logins")
        print("  Barber/admin : barber@booknbuzz.com / barber123")
        print("  Customer     : alex@example.com / password123")


if __name__ == "__main__":
    run()
