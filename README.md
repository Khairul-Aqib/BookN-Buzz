# BookN'Buzz — Barber Shop Booking System

A barber shop booking web app built for a university Software Engineering
project. It is implemented with a clean **Model–Template–View (MTV)**
architecture using **Python (Django)** and **SQLite** only.

- **Model** → `bookings/models/` (Django ORM classes mapping to the class
  diagram — one file per entity) on Django's default SQLite backend with
  **migrations**.
- **View** → `bookings/views/` + `bookings/urls.py` (function-based views,
  grouped into a `user/` area and a `barber/` area, protected with
  `@login_required` and a custom `@barber_required`).
- **Template** → `bookings/templates/` (Django Template Language: `base.html`
  + `user/` and `barber/` page folders) and `bookings/static/` (CSS, images,
  vanilla-JS calendars).

No DRF, no MySQL/Postgres, no JS frameworks — just Django, its ORM on SQLite,
the Django template engine and plain HTML/CSS.

## Quick start

The project lives in the `BookNBuzz/` folder (it holds `manage.py`).

```powershell
# from the repo root
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows (PowerShell)
# source .venv/bin/activate       # macOS / Linux

cd BookNBuzz

# 1. install dependencies
pip install -r requirements.txt

# 2. create the database from migrations
python manage.py migrate

# 3. load demo data
python manage.py seed_demo

# 4. run the app
python manage.py runserver
```

Then open **http://localhost:8000**.

## Demo login credentials

| Role           | Email                    | Password      |
|----------------|--------------------------|---------------|
| Barber / admin | `marcus@booknbuzz.com`   | `barber123`   |
| Barber         | `theo@booknbuzz.com`     | `barber123`   |
| Barber         | `aisha@booknbuzz.com`    | `barber123`   |
| Customer       | `alex@example.com`       | `password123` |
| Customer       | `sam@example.com`        | `password123` |
| Customer       | `jordan@example.com`     | `password123` |

`marcus@booknbuzz.com` is also a Django superuser, so it can sign in to the
admin site at **/admin**. You can register a brand-new customer from the
**Sign up** page.

## Architecture → class diagram mapping

`bookings/models/` contains the ORM models that map directly to the class
diagram (one file per entity):

```
User (custom auth user, role = 'customer' | 'barber')   -- initials, unread_count()
Service                                                 -- packages
Availability     -- a barber's weekly hours / blocked days; open_slots()
Booking          -- associates Customer + Barber + Service; compute_total()
Notification     -- belongs to a User
```

A single `User` model carries a `role` flag (the barber is also the shop admin).
`Booking` has foreign keys to a customer `User`, a barber `User` and a
`Service`. All persistence goes through the Django ORM.

## Data model (SQLite via migrations)

| Table           | Key columns                                                                 |
|-----------------|------------------------------------------------------------------------------|
| `users`         | id, name, email, password, role (`customer`/`barber`), phone, is_staff      |
| `services`      | id, name, description, duration_minutes, price, image, active               |
| `availability`  | id, barber_id→users, weekday, date, start_time, end_time, is_blocked        |
| `bookings`      | id, customer_id→users, barber_id→users, service_id→services, mode (`walk_in`/`mobile`), date, time_slot, service_address, status, total_price, created_at |
| `notifications` | id, user_id→users, message, is_read, created_at                             |

A partial `UniqueConstraint` (`idx_no_double_booking`) prevents double-booking
the same barber for the same date + time slot (cancelled bookings excluded).

## Use cases → code map

Every use case is an identifiable Django view (named URL).

**Customer** (`bookings/views.py`)

| Use case               | URL name                                              |
|------------------------|-------------------------------------------------------|
| Register Account       | `auth_register`                                       |
| Login / Logout         | `auth_login` / `auth_logout`                          |
| Browse Packages        | `customer_packages`, `customer_service_detail`        |
| Make Booking           | `customer_book` → `customer_book_times` → `customer_confirm_booking` |
| (live time slots, JSON) | `customer_book_slots`                                |
| View My Bookings       | `customer_my_bookings`                                |
| Cancel Booking         | `customer_cancel_booking`                             |
| View Notifications     | `customer_notifications`                              |
| My Account (profile)   | `customer_account`                                    |

**Barber / admin** (`bookings/views.py`)

| Use case                 | URL name                                                            |
|--------------------------|--------------------------------------------------------------------|
| View Dashboard           | `barber_dashboard`                                                  |
| Manage Customers         | `barber_customers`                                                  |
| Manage Items & Services  | `barber_services`, `barber_service_new/edit/delete`                |
| View Sales               | `barber_sales`                                                      |
| Create Barber Account    | `barber_barber_new`                                                 |
| Manage Availability      | `barber_availability`, `barber_set_weekday`, `barber_toggle_block` |
| Manage Bookings          | `barber_bookings` (per-date + "pending, all dates")                |
| Confirm / Claim / Release| `barber_confirm_booking`, `barber_claim_booking`, `barber_release_booking` |
| Update Booking Status    | `barber_update_status` (→ creates a Notification)                  |
| Profile                  | `barber_profile`                                                    |

## Booking process flow

Customer logs in → browses packages → picks a service → **chooses a barber** →
sees only that barber's open time slots (inside their weekly hours, not on a
blocked day, not already booked, not in the past) → chooses mode (walk-in or
mobile; mobile requires a service address) → confirms → booking is saved as
**pending** assigned to that barber, plus a notification → the barber **confirms**
it (pending → confirmed) and later marks it **completed**/**cancelled** → the
customer sees the change in *My Bookings* and *Notifications*.

Legacy **unclaimed** bookings (barber = N/A) can still be **claimed** by any
barber from the shared Bookings page, and a confirmed booking can be
**released** back to the pool.

## Mobile service fee

A flat **RM25.00** fee applies to **mobile** bookings only. It is defined once
as `MOBILE_SERVICE_FEE` in `bookings/models/booking.py`, shown as its own line on the
booking summary, and computed/enforced **server-side** into `total_price` on
confirm (the client total is never trusted). Sales, My Bookings and Manage
Bookings all show the fee-inclusive total.

## Security / validation notes

- Passwords are hashed by Django's auth system (never stored in plain text).
- Session auth with `@login_required` and a custom `@barber_required` role gate
  (`bookings/decorators.py`).
- CSRF protection on every POST form (`{% csrf_token %}`).
- The ORM parameterizes all queries.
- Server-side validation with the messages framework throughout.
- Double-booking is prevented in code **and** by a database unique constraint.
- Every booking rule (no past / blocked / out-of-hours / double-booked slots) is
  re-checked in the views on confirm.

## Project structure

Three similarly-named things, each playing a different role:

- **`BookNBuzz/`** (outer folder) — the project root you run commands from; it
  just holds `manage.py` and the two packages below.
- **`booknbuzz/`** (config package) — Django's project configuration: site-wide
  settings, the root URL map, and the WSGI/ASGI server entry points. It contains
  no features, only wiring. `manage.py` points Django at `booknbuzz.settings`.
- **`bookings/`** (the app) — all the actual functionality (models, views,
  templates, etc.).

```
BookNBuzz/                    # project ROOT (run manage.py here)
├─ manage.py
├─ requirements.txt
├─ booknbuzz/                 # project CONFIG package (no features, just wiring)
│  ├─ settings.py             #   global settings (apps, DB, auth, static…)
│  ├─ urls.py                 #   root URL map (/admin, / → home, include app)
│  ├─ wsgi.py  asgi.py        #   server entry points
│  └─ __init__.py
└─ bookings/                  # the APP — all the real code
   ├─ models/                 # MODEL — one file per entity
   │  ├─ user.py  service.py  booking.py  availability.py  notification.py
   ├─ views/                  # VIEW — grouped by audience
   │  ├─ helpers.py           #   shared helpers/constants
   │  ├─ user/                #   auth + customer use cases
   │  │  ├─ auth_views.py  customer_views.py
   │  └─ barber/              #   barber/admin management area
   │     ├─ dashboard_views.py  service_views.py
   │     ├─ availability_views.py  booking_views.py
   ├─ templates/              # TEMPLATE
   │  ├─ base.html
   │  ├─ user/   barber/   auth/   account/
   ├─ static/                 # css/, images/, js/ (booking + bookings calendars)
   ├─ urls.py                 # URL routes
   ├─ decorators.py           # barber_required role gate
   ├─ profile_service.py      # shared "edit my account" logic
   ├─ context_processors.py   # current_user / unread_count / mobile_fee
   ├─ admin.py                # admin registrations
   ├─ templatetags/booknbuzz_extras.py   # money + tojson filters
   ├─ management/commands/seed_demo.py    # demo-data loader
   └─ migrations/
```

## Resetting the database

Re-running `python manage.py seed_demo` wipes the demo rows and rebuilds them.
To rebuild the schema from scratch, delete `booknbuzz.db` and run
`python manage.py migrate` again, then `python manage.py seed_demo`.
