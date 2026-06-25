"""
model.py - the MODEL layer of the MTV architecture.

Object-oriented classes that map one-to-one to the BookN'Buzz class diagram:

    User (base)
    +-- Customer            (role = 'customer')
    +-- Barber              (role = 'barber')
    Service
    Booking                 (associates Customer + Barber + Service)
    Availability            (belongs to a Barber)
    Notification            (belongs to a User)

The classes hold data + behaviour; all SQL goes through the helpers in db.py.
"""

from datetime import datetime, date as date_cls, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

import db


# --------------------------------------------------------------------------- #
#  Shop-wide settings / constants
# --------------------------------------------------------------------------- #
# Flat surcharge added to a booking when the barber travels to the customer
# (mobile mode). Walk-in bookings have no fee. Defined here ONCE so every layer
# - booking confirm, the booking summary, seed data - uses the same value and
# it can be changed in a single place.
MOBILE_SERVICE_FEE = 25.0


# --------------------------------------------------------------------------- #
#  User  (base class)
# --------------------------------------------------------------------------- #
class User:
    """Base class for everyone who can log in. Subclassed by Customer/Barber."""

    role = None  # overridden by subclasses

    def __init__(self, id=None, name=None, email=None, password_hash=None,
                 role=None, phone=None):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.role = role or self.__class__.role
        self.phone = phone

    @property
    def initials(self):
        """1-2 letter initials from the name, for avatar fallbacks in the UI."""
        parts = [p for p in (self.name or "").split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][0].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    # ---- password handling -------------------------------------------------
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # ---- persistence -------------------------------------------------------
    def save(self):
        """Insert a new user and return its id."""
        self.id = db.execute(
            """INSERT INTO users (name, email, password_hash, role, phone)
               VALUES (?, ?, ?, ?, ?)""",
            (self.name, self.email, self.password_hash, self.role, self.phone),
        )
        return self.id

    def update_profile(self, name, phone):
        self.name, self.phone = name, phone
        db.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?",
                   (name, phone, self.id))

    def update_account(self, name, email, phone):
        """Persist edits to this user's own details (name, email, phone)."""
        self.name, self.email, self.phone = name, email, phone
        db.execute("UPDATE users SET name = ?, email = ?, phone = ? WHERE id = ?",
                   (name, email, phone, self.id))

    def change_password(self, raw_password):
        """Hash and persist a new password for this user."""
        self.set_password(raw_password)
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                   (self.password_hash, self.id))

    # ---- factory helpers ---------------------------------------------------
    @staticmethod
    def _wrap(row):
        """Turn a DB row into the correct subclass instance."""
        if row is None:
            return None
        cls = Barber if row["role"] == "barber" else Customer
        return cls(id=row["id"], name=row["name"], email=row["email"],
                   password_hash=row["password_hash"], role=row["role"],
                   phone=row["phone"])

    @classmethod
    def get(cls, user_id):
        return cls._wrap(db.query("SELECT * FROM users WHERE id = ?",
                                  (user_id,), one=True))

    @classmethod
    def find_by_email(cls, email):
        return cls._wrap(db.query("SELECT * FROM users WHERE email = ?",
                                  (email,), one=True))

    @classmethod
    def email_exists(cls, email):
        return db.query("SELECT 1 FROM users WHERE email = ?",
                        (email,), one=True) is not None

    @classmethod
    def email_taken_by_other(cls, email, user_id):
        """True if a DIFFERENT user already uses this email (uniqueness check
        for profile edits, where keeping your own email must be allowed)."""
        return db.query("SELECT 1 FROM users WHERE email = ? AND id != ?",
                        (email, user_id), one=True) is not None


# --------------------------------------------------------------------------- #
#  Customer
# --------------------------------------------------------------------------- #
class Customer(User):
    role = "customer"

    def bookings(self):
        return Booking.for_customer(self.id)

    def notifications(self):
        return Notification.for_user(self.id)

    def unread_count(self):
        return Notification.unread_count(self.id)


# --------------------------------------------------------------------------- #
#  Barber  (also the admin user)
# --------------------------------------------------------------------------- #
class Barber(User):
    role = "barber"

    @classmethod
    def all(cls):
        rows = db.query("SELECT * FROM users WHERE role = 'barber' ORDER BY name")
        return [cls._wrap(r) for r in rows]

    @classmethod
    def first(cls):
        row = db.query("SELECT * FROM users WHERE role = 'barber' ORDER BY id LIMIT 1",
                       one=True)
        return cls._wrap(row)

    # ---- dashboard stats (shop-wide: every barber sees all bookings) -------
    def todays_bookings(self):
        today = date_cls.today().isoformat()
        return Booking.for_date(today)

    def dashboard_stats(self):
        today = date_cls.today().isoformat()
        row = db.query(
            """SELECT
                 COUNT(*)                                           AS total,
                 SUM(CASE WHEN status = 'pending'    THEN 1 ELSE 0 END) AS pending,
                 SUM(CASE WHEN barber_id IS NULL
                          AND status NOT IN ('cancelled','completed')
                                                     THEN 1 ELSE 0 END) AS unclaimed,
                 SUM(CASE WHEN date = ?              THEN 1 ELSE 0 END) AS today,
                 SUM(CASE WHEN status = 'completed' THEN total_price ELSE 0 END) AS revenue
               FROM bookings""",
            (today,), one=True)
        return {
            "total": row["total"] or 0,
            "pending": row["pending"] or 0,
            "unclaimed": row["unclaimed"] or 0,
            "today": row["today"] or 0,
            "revenue": row["revenue"] or 0.0,
        }


# --------------------------------------------------------------------------- #
#  Service  (a haircut / beard / grooming package)
# --------------------------------------------------------------------------- #
class Service:
    def __init__(self, id=None, name=None, description=None,
                 duration_minutes=30, price=0.0, image=None, active=1):
        self.id = id
        self.name = name
        self.description = description
        self.duration_minutes = int(duration_minutes)
        self.price = float(price)
        self.image = image
        self.active = int(active)

    @staticmethod
    def _wrap(row):
        if row is None:
            return None
        return Service(id=row["id"], name=row["name"],
                       description=row["description"],
                       duration_minutes=row["duration_minutes"],
                       price=row["price"], image=row["image"],
                       active=row["active"])

    @classmethod
    def get(cls, service_id):
        return cls._wrap(db.query("SELECT * FROM services WHERE id = ?",
                                  (service_id,), one=True))

    @classmethod
    def all(cls, active_only=False):
        sql = "SELECT * FROM services"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY name"
        return [cls._wrap(r) for r in db.query(sql)]

    def save(self):
        if self.id is None:
            self.id = db.execute(
                """INSERT INTO services
                   (name, description, duration_minutes, price, image, active)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self.name, self.description, self.duration_minutes,
                 self.price, self.image, self.active))
        else:
            db.execute(
                """UPDATE services SET name = ?, description = ?,
                   duration_minutes = ?, price = ?, image = ?, active = ?
                   WHERE id = ?""",
                (self.name, self.description, self.duration_minutes,
                 self.price, self.image, self.active, self.id))
        return self.id

    @classmethod
    def delete(cls, service_id):
        db.execute("DELETE FROM services WHERE id = ?", (service_id,))


# --------------------------------------------------------------------------- #
#  Availability  (a barber's working hours / blocked days)
# --------------------------------------------------------------------------- #
class Availability:
    SLOT_MINUTES = 30  # granularity of generated time slots

    def __init__(self, id=None, barber_id=None, weekday=None, date=None,
                 start_time=None, end_time=None, is_blocked=0):
        self.id = id
        self.barber_id = barber_id
        self.weekday = weekday
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.is_blocked = int(is_blocked)

    @staticmethod
    def _wrap(row):
        return Availability(id=row["id"], barber_id=row["barber_id"],
                            weekday=row["weekday"], date=row["date"],
                            start_time=row["start_time"], end_time=row["end_time"],
                            is_blocked=row["is_blocked"])

    @classmethod
    def for_barber(cls, barber_id):
        rows = db.query(
            """SELECT * FROM availability WHERE barber_id = ?
               ORDER BY is_blocked, weekday, date, start_time""",
            (barber_id,))
        return [cls._wrap(r) for r in rows]

    @classmethod
    def blocked_dates(cls, barber_id):
        """Specific dates the barber has blocked off (for the calendar UI)."""
        rows = db.query(
            """SELECT DISTINCT date FROM availability
               WHERE barber_id = ? AND is_blocked = 1 AND date IS NOT NULL""",
            (barber_id,))
        return [r["date"] for r in rows]

    @classmethod
    def working_weekdays(cls, barber_id):
        """Weekdays (0=Mon..6=Sun) the barber has working hours on."""
        rows = db.query(
            """SELECT DISTINCT weekday FROM availability
               WHERE barber_id = ? AND is_blocked = 0 AND weekday IS NOT NULL""",
            (barber_id,))
        return sorted(r["weekday"] for r in rows)

    @classmethod
    def is_blocked_date(cls, barber_id, on_date):
        """True if the barber blocked this exact date (server-side guard)."""
        return db.query(
            """SELECT 1 FROM availability
               WHERE barber_id = ? AND date = ? AND is_blocked = 1""",
            (barber_id, on_date), one=True) is not None

    # ---- weekly schedule editing (one row per weekday) --------------------
    @classmethod
    def weekly_schedule(cls, barber_id):
        """Return a list of 7 dicts (Mon..Sun) describing the working week.

        Each dict: {weekday, open, start, end}. Days with no hours come back as
        closed with sensible default times pre-filled for when they're opened.
        """
        rows = db.query(
            """SELECT weekday, start_time, end_time FROM availability
               WHERE barber_id = ? AND is_blocked = 0
                 AND weekday IS NOT NULL AND date IS NULL""",
            (barber_id,))
        by_day = {}
        for r in rows:
            by_day.setdefault(r["weekday"], (r["start_time"], r["end_time"]))

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

    @classmethod
    def clear_weekday(cls, barber_id, weekday):
        """Remove the recurring working hours for a weekday (closes the day)."""
        db.execute(
            """DELETE FROM availability
               WHERE barber_id = ? AND weekday = ?
                 AND is_blocked = 0 AND date IS NULL""",
            (barber_id, weekday))

    @classmethod
    def set_weekday(cls, barber_id, weekday, start, end):
        """Replace a weekday's working hours with a single window."""
        cls.clear_weekday(barber_id, weekday)
        db.execute(
            """INSERT INTO availability
               (barber_id, weekday, date, start_time, end_time, is_blocked)
               VALUES (?, ?, NULL, ?, ?, 0)""",
            (barber_id, weekday, start, end))

    @classmethod
    def toggle_block(cls, barber_id, on_date):
        """Block the date if free, or unblock it if already blocked.

        Returns True if the date is now blocked, False if now unblocked.
        """
        existing = db.query(
            """SELECT id FROM availability
               WHERE barber_id = ? AND date = ? AND is_blocked = 1""",
            (barber_id, on_date), one=True)
        if existing:
            db.execute(
                """DELETE FROM availability
                   WHERE barber_id = ? AND date = ? AND is_blocked = 1""",
                (barber_id, on_date))
            return False
        db.execute(
            """INSERT INTO availability
               (barber_id, weekday, date, start_time, end_time, is_blocked)
               VALUES (?, NULL, ?, '00:00', '23:59', 1)""",
            (barber_id, on_date))
        return True

    def save(self):
        self.id = db.execute(
            """INSERT INTO availability
               (barber_id, weekday, date, start_time, end_time, is_blocked)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (self.barber_id, self.weekday, self.date,
             self.start_time, self.end_time, self.is_blocked))
        return self.id

    @classmethod
    def delete(cls, avail_id, barber_id):
        db.execute("DELETE FROM availability WHERE id = ? AND barber_id = ?",
                   (avail_id, barber_id))

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
    def booked_intervals(cls, barber_id, on_date):
        """[(start_min, end_min)] for this barber's active bookings on a date.

        Each booking occupies its slot start through start + service duration,
        so a 60-min service blocks the slots it overlaps - not just its start.
        """
        rows = db.query(
            """SELECT b.time_slot, s.duration_minutes
               FROM bookings b
               JOIN services s ON s.id = b.service_id
               WHERE b.barber_id = ? AND b.date = ? AND b.status != 'cancelled'""",
            (barber_id, on_date))
        intervals = []
        for r in rows:
            start = cls._to_minutes(r["time_slot"])
            if start is None:
                continue
            intervals.append((start, start + int(r["duration_minutes"] or 0)))
        return intervals

    @classmethod
    def open_slots(cls, barber_id, on_date, duration_minutes=30):
        """Return the list of free 'HH:MM' slots for THIS barber on a date.

        A slot is offered only when it (a) falls inside the barber's working
        hours for that weekday, (b) is not on one of the barber's blocked days,
        (c) leaves room for the full service before closing time, and (d) does
        not overlap a booking that barber already has. Past slots for today are
        also hidden.
        """
        try:
            d = datetime.strptime(on_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return []

        weekday = d.weekday()  # Monday = 0

        # Whole-day block for this exact date?
        blocked = db.query(
            """SELECT 1 FROM availability
               WHERE barber_id = ? AND date = ? AND is_blocked = 1""",
            (barber_id, on_date), one=True)
        if blocked:
            return []

        # Working-hour windows: recurring weekly rows for this weekday.
        windows = db.query(
            """SELECT start_time, end_time FROM availability
               WHERE barber_id = ? AND is_blocked = 0
                 AND weekday = ? AND date IS NULL
               ORDER BY start_time""",
            (barber_id, weekday))
        if not windows:
            return []

        # This barber's existing bookings (as minute intervals) for the date.
        busy = cls.booked_intervals(barber_id, on_date)

        now = datetime.now()
        slots = []
        for w in windows:
            cursor = datetime.strptime(w["start_time"], "%H:%M")
            end = datetime.strptime(w["end_time"], "%H:%M")
            # Last start time that still leaves room for the service.
            while cursor + timedelta(minutes=duration_minutes) <= end:
                label = cursor.strftime("%H:%M")
                slot_start = cursor.hour * 60 + cursor.minute
                slot_end = slot_start + duration_minutes
                overlaps = any(slot_start < b_end and b_start < slot_end
                               for b_start, b_end in busy)
                slot_dt = datetime.combine(d, cursor.time())
                if not overlaps and slot_dt > now:
                    slots.append(label)
                cursor += timedelta(minutes=cls.SLOT_MINUTES)
        return sorted(set(slots))


# --------------------------------------------------------------------------- #
#  Booking  (associates Customer + Barber + Service)
# --------------------------------------------------------------------------- #
class Booking:
    STATUSES = ("pending", "confirmed", "completed", "cancelled")

    def __init__(self, id=None, customer_id=None, barber_id=None,
                 service_id=None, mode="walk_in", date=None, time_slot=None,
                 service_address=None, status="pending", total_price=0.0,
                 created_at=None):
        self.id = id
        self.customer_id = customer_id
        self.barber_id = barber_id
        self.service_id = service_id
        self.mode = mode
        self.date = date
        self.time_slot = time_slot
        self.service_address = service_address
        self.status = status
        self.total_price = total_price
        self.created_at = created_at

    # ---- pricing -----------------------------------------------------------
    @staticmethod
    def mobile_fee(mode):
        """The surcharge for a booking mode: RM25 for mobile, nothing for
        walk-in. Uses the single MOBILE_SERVICE_FEE constant."""
        return MOBILE_SERVICE_FEE if mode == "mobile" else 0.0

    @classmethod
    def compute_total(cls, service_price, mode):
        """Authoritative total = package price + any mobile fee. Always used
        server-side on confirm so the client total is never trusted."""
        return float(service_price) + cls.mobile_fee(mode)

    # ---- creation ----------------------------------------------------------
    @classmethod
    def is_slot_free(cls, barber_id, on_date, time_slot):
        """True if THIS barber has no non-cancelled booking at this date+slot."""
        taken = db.query(
            """SELECT 1 FROM bookings
               WHERE barber_id = ? AND date = ? AND time_slot = ?
                 AND status != 'cancelled'""",
            (barber_id, on_date, time_slot), one=True)
        return taken is None

    def save(self):
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.id = db.execute(
            """INSERT INTO bookings
               (customer_id, barber_id, service_id, mode, date, time_slot,
                service_address, status, total_price, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.customer_id, self.barber_id, self.service_id, self.mode,
             self.date, self.time_slot, self.service_address, self.status,
             self.total_price, self.created_at))
        return self.id

    # ---- queries (returned as dict rows joined with names) -----------------
    _SELECT = """
        SELECT b.*, s.name AS service_name, s.duration_minutes,
               c.name AS customer_name, c.email AS customer_email,
               c.phone AS customer_phone, bar.name AS barber_name
        FROM bookings b
        JOIN services s   ON s.id   = b.service_id
        JOIN users    c   ON c.id   = b.customer_id
        LEFT JOIN users bar ON bar.id = b.barber_id
    """

    @classmethod
    def get(cls, booking_id):
        return db.query(cls._SELECT + " WHERE b.id = ?", (booking_id,), one=True)

    @classmethod
    def for_customer(cls, customer_id):
        return db.query(
            cls._SELECT + " WHERE b.customer_id = ? ORDER BY b.date DESC, b.time_slot",
            (customer_id,))

    @classmethod
    def list(cls, on_date=None, status=None):
        """All bookings shop-wide, optionally filtered by date and/or status.

        Unclaimed bookings (no barber) sort to the top so barbers see what is
        waiting to be claimed first.
        """
        sql = cls._SELECT + " WHERE 1 = 1"
        params = []
        if on_date:
            sql += " AND b.date = ?"
            params.append(on_date)
        if status:
            sql += " AND b.status = ?"
            params.append(status)
        sql += (" ORDER BY (b.barber_id IS NOT NULL), "
                "b.date DESC, b.time_slot")
        return db.query(sql, tuple(params))

    @classmethod
    def for_date(cls, on_date, status=None):
        return cls.list(on_date=on_date, status=status)

    @classmethod
    def for_day(cls, on_date, status=None):
        """Bookings on a single date, earliest time first (per-date view)."""
        sql = cls._SELECT + " WHERE b.date = ?"
        params = [on_date]
        if status:
            sql += " AND b.status = ?"
            params.append(status)
        sql += " ORDER BY b.time_slot"
        return db.query(sql, tuple(params))

    @classmethod
    def pending_all(cls):
        """Every pending / unclaimed booking across all dates (soonest first)."""
        return db.query(
            cls._SELECT +
            " WHERE b.status = 'pending' OR b.barber_id IS NULL"
            " ORDER BY b.date, b.time_slot")

    @classmethod
    def pending_count(cls):
        row = db.query(
            "SELECT COUNT(*) AS c FROM bookings "
            "WHERE status = 'pending' OR barber_id IS NULL", one=True)
        return row["c"] if row else 0

    @classmethod
    def counts_by_date(cls):
        """Map of date -> number of active (non-cancelled) bookings, for the
        calendar's busy-day dots."""
        rows = db.query(
            "SELECT date, COUNT(*) AS c FROM bookings "
            "WHERE status != 'cancelled' GROUP BY date")
        return {r["date"]: r["c"] for r in rows}

    @classmethod
    def all(cls):
        return cls.list()

    # ---- confirm (owning barber accepts their assigned pending booking) ----
    @classmethod
    def confirm(cls, booking_id, barber_id):
        """Confirm a pending booking already assigned to this barber.

        Customers now pick the barber, so the barber's job is simply to accept
        (pending -> confirmed) the appointment that arrived assigned to them.
        Returns True if the booking is now confirmed for this barber.
        """
        db.execute(
            """UPDATE bookings SET status = 'confirmed'
               WHERE id = ? AND barber_id = ? AND status = 'pending'""",
            (booking_id, barber_id))
        row = db.query(
            "SELECT status FROM bookings WHERE id = ? AND barber_id = ?",
            (booking_id, barber_id), one=True)
        return row is not None and row["status"] == "confirmed"

    # ---- claiming (any barber can claim a LEGACY unclaimed booking) --------
    @classmethod
    def claim(cls, booking_id, barber_id):
        """Claim an unclaimed pending booking: assign the barber AND confirm it.

        Pending -> Confirmed happens here (by claiming), not via the dropdown.
        Returns True if it worked.
        """
        db.execute(
            """UPDATE bookings SET barber_id = ?, status = 'confirmed'
               WHERE id = ? AND barber_id IS NULL AND status = 'pending'""",
            (barber_id, booking_id))
        row = db.query("SELECT barber_id FROM bookings WHERE id = ?",
                       (booking_id,), one=True)
        return row is not None and row["barber_id"] == barber_id

    @classmethod
    def release(cls, booking_id, barber_id):
        """Release a confirmed booking back to the pool: unclaim AND set pending.

        Confirmed -> Pending happens here (by releasing). Only the owning barber
        may release, and only while the booking is still confirmed.
        """
        db.execute(
            """UPDATE bookings SET barber_id = NULL, status = 'pending'
               WHERE id = ? AND barber_id = ? AND status = 'confirmed'""",
            (booking_id, barber_id))

    # ---- status changes ----------------------------------------------------
    @classmethod
    def set_status(cls, booking_id, status):
        db.execute("UPDATE bookings SET status = ? WHERE id = ?",
                   (status, booking_id))

    @classmethod
    def cancel(cls, booking_id, customer_id):
        """Customer-initiated cancel (only their own, only if not finished)."""
        db.execute(
            """UPDATE bookings SET status = 'cancelled'
               WHERE id = ? AND customer_id = ?
                 AND status IN ('pending', 'confirmed')""",
            (booking_id, customer_id))

    # ---- sales report ------------------------------------------------------
    @classmethod
    def sales_report(cls):
        """Revenue from completed bookings, grouped by service."""
        rows = db.query(
            """SELECT s.name AS service_name,
                      COUNT(*) AS sold,
                      SUM(b.total_price) AS revenue
               FROM bookings b
               JOIN services s ON s.id = b.service_id
               WHERE b.status = 'completed'
               GROUP BY b.service_id
               ORDER BY revenue DESC""")
        total = db.query(
            "SELECT COALESCE(SUM(total_price), 0) AS total FROM bookings "
            "WHERE status = 'completed'", one=True)["total"]
        return rows, total


# --------------------------------------------------------------------------- #
#  Notification
# --------------------------------------------------------------------------- #
class Notification:
    def __init__(self, id=None, user_id=None, message=None, is_read=0,
                 created_at=None):
        self.id = id
        self.user_id = user_id
        self.message = message
        self.is_read = is_read
        self.created_at = created_at

    @classmethod
    def push(cls, user_id, message):
        """Create a notification for a user (called on status changes etc.)."""
        return db.execute(
            """INSERT INTO notifications (user_id, message, is_read, created_at)
               VALUES (?, ?, 0, ?)""",
            (user_id, message, datetime.now().strftime("%Y-%m-%d %H:%M")))

    @classmethod
    def for_user(cls, user_id):
        return db.query(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC, id DESC",
            (user_id,))

    @classmethod
    def unread_count(cls, user_id):
        row = db.query(
            "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,), one=True)
        return row["c"] if row else 0

    @classmethod
    def mark_all_read(cls, user_id):
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?",
                   (user_id,))
