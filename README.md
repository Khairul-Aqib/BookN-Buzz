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

Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1      # Windows (PowerShell)
# venv\Scripts\activate        # Windows (cmd)
# source venv/bin/activate     # macOS / Linux
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
| Barber / admin | `marcus@booknbuzz.com`  | `barber123`   |
| Barber / admin | `theo@booknbuzz.com`    | `barber123`   |
| Barber / admin | `aisha@booknbuzz.com`   | `barber123`   |
| Customer       | `alex@example.com`      | `password123` |
| Customer       | `sam@example.com`       | `password123` |
| Customer       | `jordan@example.com`    | `password123` |

The demo data seeds **3 barbers** (all `barber123`) and **6 customers** (all
`password123`); the remaining customers are `nadia@`, `weijie@` and `priya@`
`example.com`. You can also register a brand-new customer account from the
**Sign up** page, and any logged-in user can edit their own details / password
from the **My Account** (customer) or **Profile** (barber) page.

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
| Pick Barber            | `customer.book`                                   |
| Choose Mode + Date + Time Slot + Service Address | `customer.book_times` (walk-in / mobile) |
| Make Booking           | `customer.confirm_booking`                        |
| View My Bookings       | `customer.my_bookings`                            |
| Cancel Booking         | `customer.cancel_booking`                         |
| View Notifications     | `customer.notifications`                          |
| View / Edit My Account | `customer.account` (details + change password)    |

**Barber / admin** (`views/barber.py`)

| Use case                 | Route / function                                       |
|--------------------------|--------------------------------------------------------|
| View Dashboard           | `barber.dashboard`                                     |
| Manage Customers         | `barber.customers`                                     |
| Manage Items & Services  | `barber.services`, `service_new`, `service_edit`, `service_delete` |
| View Sales               | `barber.sales`                                         |
| Create Barber Account    | `barber.barber_new`                                    |
| Manage Availability      | `barber.availability`, `availability_delete`           |
| Manage Bookings          | `barber.bookings` (confirm / claim / release)          |
| Update Booking Status    | `barber.update_status` (→ creates a Notification)      |
| Edit Profile             | `barber.profile` (details + change password)           |

## Booking process flow

Customer logs in → browses packages → picks a service → **picks a barber** →
chooses mode (walk-in or mobile; mobile requires a service address) and a date →
the system shows only that barber's time slots that fit their availability and
are not already booked → confirms → the **total is computed server-side**
(package price, plus a flat **RM25 mobile fee** for mobile bookings) → the
booking is saved as **pending**, assigned to the chosen barber, plus a
notification → that barber **confirms** it (pending → confirmed) and later marks
it **completed / cancelled** → the customer sees the change in *My Bookings* and
*Notifications*.

### Mobile service fee

Mobile bookings (the barber travels to the customer) add a flat surcharge on top
of the package price; walk-in bookings have no fee. The amount is defined **once**
as `MOBILE_SERVICE_FEE` in `model.py` and applied through `Booking.compute_total`,
which is the single source of truth used by the confirm flow, the booking summary
and the seed data. The booking summary shows it as its own line:

```
Package      RM18.00
Mobile fee   RM25.00
Total        RM43.00
```

The fee line is hidden for walk-in bookings, and the total is always recomputed
server-side on confirm — the client-side figure is never trusted.

### Shared bookings & claiming

All barber accounts see **every** booking. New bookings arrive already assigned
to the barber the customer chose (status **pending**), and that barber
**confirms** them. Any legacy **unclaimed** booking (`barber_id` NULL) shows its
barber as **N/A** with a **Claim** button; once claimed it shows that barber's
name, and the owner can **Release** it back to the pool. `barber_id` on
`bookings` is nullable, and the double-booking unique index is **per-barber**
(`barber_id, date, time_slot`, cancelled excluded) so two barbers can each hold
the same slot but one barber can't be booked twice.

## Security / validation notes

- Passwords are hashed with `werkzeug.security` (never stored in plain text).
- Session-based auth with `@login_required` and `@barber_required` decorators
  (`auth_utils.py`).
- Every SQL query is parameterized — no user input is formatted into SQL.
- Server-side validation with flash messages and friendly errors throughout.
- Double-booking is prevented in code **and** by a database unique index.

## Project structure

```
app.py             # creates the Flask app, registers blueprints (View)
db.py              # sqlite3 connection + CRUD helpers (Model)
model.py           # OOP classes + MOBILE_SERVICE_FEE constant (Model)
schema.sql         # table definitions
seed.py            # builds the DB + demo data
auth_utils.py      # session helpers + access-control decorators
profile_service.py # shared account/password update logic + validation
requirements.txt   # Flask only
views/             # auth.py, customer.py, barber.py (View blueprints)
templates/         # base.html + page templates, incl. account/ (Template)
static/            # css/, images/, js/calendar.js (booking calendar)
```

## Resetting the database

Re-running `python seed.py` wipes `booknbuzz.db` and rebuilds it with fresh
demo data.
