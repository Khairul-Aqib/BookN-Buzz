-- BookN'Buzz - SQLite schema
-- Tables map directly to the Model classes in model.py.
-- Foreign keys connect the associations shown in the class diagram:
--   Booking -> Customer (users), Barber (users), Service
--   Availability -> Barber (users)
--   Notification -> User (users)

PRAGMA foreign_keys = ON;

-- A single users table holds both Customer and Barber rows (role column).
-- In the Model this maps to the base class `User` subclassed by `Customer`
-- and `Barber`.
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('customer', 'barber')),
    phone         TEXT
);

-- Services / packages offered by the shop.
CREATE TABLE IF NOT EXISTS services (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    description      TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    price            REAL    NOT NULL DEFAULT 0,
    image            TEXT,
    active           INTEGER NOT NULL DEFAULT 1
);

-- Barber working hours. A row is either a recurring weekly block
-- (weekday set, date NULL) or a specific-date entry. is_blocked = 1
-- marks a blocked day/slot the barber is unavailable for.
CREATE TABLE IF NOT EXISTS availability (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    barber_id  INTEGER NOT NULL,
    weekday    INTEGER,                 -- 0 = Monday ... 6 = Sunday (NULL if date-specific)
    date       TEXT,                    -- YYYY-MM-DD (NULL if recurring)
    start_time TEXT    NOT NULL,        -- HH:MM
    end_time   TEXT    NOT NULL,        -- HH:MM
    is_blocked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (barber_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Bookings link a Customer, a Service and a Barber. The customer now picks a
-- specific barber when booking, so barber_id is normally set at creation time
-- (status 'pending' until that barber confirms). barber_id stays nullable only
-- to support any legacy "unclaimed" bookings created before this change.
CREATE TABLE IF NOT EXISTS bookings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL,
    barber_id       INTEGER,                -- NULL = unclaimed / N/A
    service_id      INTEGER NOT NULL,
    mode            TEXT    NOT NULL CHECK (mode IN ('walk_in', 'mobile')),
    date            TEXT    NOT NULL,   -- YYYY-MM-DD
    time_slot       TEXT    NOT NULL,   -- HH:MM
    service_address TEXT,               -- required only for mobile mode
    status          TEXT    NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled')),
    total_price     REAL    NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES users (id),
    FOREIGN KEY (barber_id)   REFERENCES users (id),
    FOREIGN KEY (service_id)  REFERENCES services (id)
);

-- Database-level guard against double-booking the SAME BARBER for the same
-- date + time slot. Because customers now choose a specific barber, two
-- different barbers can each hold the same date+slot, but one barber can't be
-- booked twice. Cancelled bookings free the slot. (SQLite treats NULLs as
-- distinct, so legacy unclaimed rows with barber_id NULL are not constrained.)
CREATE UNIQUE INDEX IF NOT EXISTS idx_no_double_booking
    ON bookings (barber_id, date, time_slot)
    WHERE status != 'cancelled';

-- Customer notifications (e.g. when a barber updates a booking status).
CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    message    TEXT    NOT NULL,
    is_read    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
