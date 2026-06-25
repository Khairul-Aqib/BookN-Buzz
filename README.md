# BookN'Buzz — Barber Shop Booking System

A barber shop booking web app built for a university Software Engineering
project. It is implemented with a clean **Model–Template–View (MTV)**
architecture using **Python (Flask)** and **SQLite** only.

- **Model** → `model.py` (OOP classes mapping to the class diagram) + `db.py`
  (SQLite connection/CRUD helpers) + `schema.sql` (table definitions).
- **View** → `views/` Flask blueprints: `auth.py`, `customer.py`, `barber.py`.
- **Template** → `templates/` (Jinja2: `base.html` + one template per page) and
  `static/` (CSS + SVG images).

No ORM, no MySQL/Postgres, no JS frameworks — just Flask, the built-in `sqlite3`
module, Jinja2 templates and plain HTML/CSS.

## Quick start

This project already has a virtual environment in the parent `BookN'Buzz`
folder. Activate it from **PowerShell** with:

```powershell
& "C:\Users\khair\Downloads\BookN'Buzz\.venv\Scripts\Activate.ps1"
```

Or create a fresh one if you prefer:

```bash
python -m venv venv
venv\Scripts\activate        # Windows (cmd)
# source venv/bin/activate   # macOS / Linux
```

Then install and run:

```bash
# 1. install the one dependency
pip install -r requirements.txt

# 2. build the database and load demo data
python seed.py

# 3. run the app
python app.py
```

Then open **http://localhost:5000**.

## Demo login credentials

| Role           | Email                   | Password      |
|----------------|-------------------------|---------------|
| Barber / admin | `barber@booknbuzz.com`  | `barber123`   |
| Customer       | `alex@example.com`      | `password123` |
| Customer       | `sam@example.com`       | `password123` |
| Customer       | `jordan@example.com`    | `password123` |

You can also register a brand-new customer account from the **Sign up** page.

## Architecture → class diagram mapping

`model.py` contains the OOP classes that map directly to the class diagram:

```
User (base)
 ├── Customer   (role = 'customer')   -- bookings(), notifications()
 └── Barber     (role = 'barber')     -- dashboard_stats(), todays_bookings()
Service                               -- CRUD for packages
Booking          -- associates Customer + Barber + Service
Availability     -- a barber's working hours / blocked days; open_slots()
Notification     -- belongs to a User
```

`User` is subclassed by `Customer` and `Barber` (inheritance). `Booking`
associates a `Customer`, a `Barber` and a `Service` (associations / foreign
keys). All SQL lives in `db.py` and is fully parameterized.

## Data model (SQLite)

| Table           | Key columns                                                                 |
|-----------------|------------------------------------------------------------------------------|
| `users`         | id, name, email, password_hash, role (`customer`/`barber`), phone           |
| `services`      | id, name, description, duration_minutes, price, image, active               |
| `availability`  | id, barber_id→users, weekday, date, start_time, end_time, is_blocked        |
| `bookings`      | id, customer_id→users, barber_id→users, service_id→services, mode (`walk_in`/`mobile`), date, time_slot, service_address, status, total_price, created_at |
| `notifications` | id, user_id→users, message, is_read, created_at                             |

A partial unique index (`idx_no_double_booking`) prevents double-booking the
same barber for the same date + time slot (cancelled bookings excluded).

## Use cases → code map

Every use case from the BookN'Buzz use-case diagram is an identifiable route.

**Customer** (`views/customer.py`, `views/auth.py`)

| Use case               | Route / function                                  |
|------------------------|---------------------------------------------------|
| Register Account       | `auth.register`                                   |
| Login / Logout         | `auth.login` / `auth.logout`                      |
| Browse Packages        | `customer.packages`, `customer.service_detail`    |
| Choose Service Mode    | `customer.book` (walk-in / mobile)                |
| Make Booking + Select Time Slot + Service Address | `customer.book` → `customer.confirm_booking` |
| View My Bookings       | `customer.my_bookings`                            |
| Cancel Booking         | `customer.cancel_booking`                         |
| View Notifications     | `customer.notifications`                          |

**Barber / admin** (`views/barber.py`)

| Use case                 | Route / function                                       |
|--------------------------|--------------------------------------------------------|
| View Dashboard           | `barber.dashboard`                                     |
| Manage Customers         | `barber.customers`                                     |
| Manage Items & Services  | `barber.services`, `service_new`, `service_edit`, `service_delete` |
| View Sales               | `barber.sales`                                         |
| Create Barber Account    | `barber.barber_new`                                    |
| Manage Availability      | `barber.availability`, `availability_delete`           |
| Manage Bookings          | `barber.bookings`                                      |
| Update Booking Status    | `barber.update_status` (→ creates a Notification)      |

## Booking process flow

Customer logs in → browses packages → picks a service → chooses mode (walk-in or
mobile; mobile requires a service address) → the system shows only time slots
that fit the shop's availability and are not already booked → confirms →
booking is saved as **pending** and **unclaimed** (no barber yet) plus a
notification → any barber can **claim** it from the shared Bookings page → the
claiming barber updates the status (pending → confirmed → completed / cancelled)
→ the customer sees the change in *My Bookings* and *Notifications*.

### Shared bookings & claiming

All barber accounts see **every** booking. An unclaimed booking shows its barber
as **N/A** with a **Claim** button; once a barber claims it, the booking shows
that barber's name (and the owner can **Release** it back to the pool). Any
barber may update the status of any booking. `barber_id` on `bookings` is
nullable (NULL = unclaimed), and the double-booking unique index is shop-wide
(`date, time_slot`) so a slot can be held only once regardless of barber.

## Security / validation notes

- Passwords are hashed with `werkzeug.security` (never stored in plain text).
- Session-based auth with `@login_required` and `@barber_required` decorators
  (`auth_utils.py`).
- Every SQL query is parameterized — no user input is formatted into SQL.
- Server-side validation with flash messages and friendly errors throughout.
- Double-booking is prevented in code **and** by a database unique index.

## Project structure

```
app.py            # creates the Flask app, registers blueprints (View)
db.py             # sqlite3 connection + CRUD helpers (Model)
model.py          # OOP classes matching the class diagram (Model)
schema.sql        # table definitions
seed.py           # builds the DB + demo data
auth_utils.py     # session helpers + access-control decorators
requirements.txt  # Flask only
views/            # auth.py, customer.py, barber.py (View blueprints)
templates/        # base.html + page templates (Template)
static/           # css/, images/, js/calendar.js (booking calendar)
```

## Resetting the database

Re-running `python seed.py` wipes `booknbuzz.db` and rebuilds it with fresh
demo data.
