"""
migrate_claim.py - one-time, in-place migration to the "claimable bookings"
model WITHOUT losing existing data.

What it does:
  * makes bookings.barber_id nullable (rebuilds the table),
  * replaces the per-barber double-booking index with a shop-wide one,
  * sets every still-pending booking to unclaimed (barber_id = NULL) so it
    shows as N/A and can be claimed by any barber.

Safe to run more than once (it detects if the DB is already migrated).
Run:  python migrate_claim.py
"""

import sqlite3

from db import DB_PATH

NEW_BOOKINGS = """
CREATE TABLE bookings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL,
    barber_id       INTEGER,
    service_id      INTEGER NOT NULL,
    mode            TEXT    NOT NULL CHECK (mode IN ('walk_in', 'mobile')),
    date            TEXT    NOT NULL,
    time_slot       TEXT    NOT NULL,
    service_address TEXT,
    status          TEXT    NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled')),
    total_price     REAL    NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES users (id),
    FOREIGN KEY (barber_id)   REFERENCES users (id),
    FOREIGN KEY (service_id)  REFERENCES services (id)
);
"""


def barber_id_is_nullable(conn):
    for col in conn.execute("PRAGMA table_info(bookings)"):
        if col[1] == "barber_id":          # (cid, name, type, notnull, ...)
            return col[3] == 0
    return False


def run():
    conn = sqlite3.connect(DB_PATH)
    try:
        if barber_id_is_nullable(conn):
            print("Database already migrated - making sure pending bookings "
                  "are unclaimed...")
        else:
            print("Migrating bookings table -> barber_id nullable ...")
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("BEGIN")
            conn.execute("ALTER TABLE bookings RENAME TO bookings_old")
            conn.executescript(NEW_BOOKINGS)
            conn.execute(
                """INSERT INTO bookings
                   (id, customer_id, barber_id, service_id, mode, date,
                    time_slot, service_address, status, total_price, created_at)
                   SELECT id, customer_id, barber_id, service_id, mode, date,
                          time_slot, service_address, status, total_price, created_at
                   FROM bookings_old""")
            conn.execute("DROP TABLE bookings_old")
            conn.execute("COMMIT")
            conn.execute("PRAGMA foreign_keys = ON")

        # Shop-wide double-booking index (replaces the old per-barber one).
        conn.execute("DROP INDEX IF EXISTS idx_no_double_booking")
        conn.execute(
            """CREATE UNIQUE INDEX idx_no_double_booking
               ON bookings (date, time_slot) WHERE status != 'cancelled'""")

        # Un-assign still-open bookings so they appear as N/A (claimable).
        changed = conn.execute(
            "UPDATE bookings SET barber_id = NULL WHERE status = 'pending'"
        ).rowcount
        conn.commit()
        print(f"  pending bookings set to unclaimed (N/A): {changed}")

        rows = conn.execute(
            "SELECT id, status, barber_id FROM bookings ORDER BY id").fetchall()
        print("  bookings now:")
        for r in rows:
            who = "N/A" if r[2] is None else f"barber {r[2]}"
            print(f"    #{r[0]:>2}  {r[1]:<10}  {who}")
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
