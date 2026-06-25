"""
migrate_barber_booking.py - in-place migration for the "customer picks the
barber" change, WITHOUT losing existing data.

What it does:
  * replaces the shop-wide double-booking index (date, time_slot) with a
    per-barber one (barber_id, date, time_slot) - so two different barbers can
    each hold the same date+slot, but a single barber can't be booked twice.

Existing rows are left untouched: any legacy unclaimed bookings (barber_id
NULL) stay claimable; bookings that already name a barber keep theirs.

Safe to run more than once. Run:  python migrate_barber_booking.py
"""

import sqlite3

from db import DB_PATH


def run():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Detect a per-barber, partial unique index already in place.
        already = False
        for row in conn.execute("PRAGMA index_list(bookings)"):
            name = row[1]
            if name == "idx_no_double_booking":
                cols = [c[2] for c in conn.execute(
                    f"PRAGMA index_info({name})")]
                already = "barber_id" in cols
        if already:
            print("Database already migrated - per-barber booking index "
                  "is in place. Nothing to do.")
            return

        print("Migrating double-booking index -> per-barber ...")
        conn.execute("DROP INDEX IF EXISTS idx_no_double_booking")
        conn.execute(
            """CREATE UNIQUE INDEX idx_no_double_booking
               ON bookings (barber_id, date, time_slot)
               WHERE status != 'cancelled'""")
        conn.commit()
        print("  index rebuilt: (barber_id, date, time_slot) "
              "WHERE status != 'cancelled'")
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
