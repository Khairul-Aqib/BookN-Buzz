"""
db.py - SQLite connection + CRUD helpers used by the Model classes.

This module keeps ALL raw sqlite3 access in one place. The Model classes in
model.py never touch sqlite3 directly; they call the helpers here. Every query
is parameterized (no string formatting of user input) to prevent SQL injection.
"""

import os
import sqlite3

from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "booknbuzz.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def _configure(conn):
    """Apply standard settings to a fresh connection."""
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Return the per-request connection, creating it on first use.

    Stored on Flask's `g` object so the same connection is reused for the whole
    request and closed automatically afterwards (see close_db / init_app).
    """
    if "db" not in g:
        g.db = _configure(sqlite3.connect(DB_PATH))
    return g.db


def close_db(exception=None):
    """Close the per-request connection (registered as a teardown handler)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """Wire the connection teardown into the Flask app."""
    app.teardown_appcontext(close_db)


# --------------------------------------------------------------------------- #
#  Generic CRUD helpers
# --------------------------------------------------------------------------- #
def query(sql, params=(), one=False):
    """Run a SELECT and return rows (or a single row when one=True)."""
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE, commit, and return the new row id."""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id


# --------------------------------------------------------------------------- #
#  Schema setup (used by seed.py)
# --------------------------------------------------------------------------- #
def init_db():
    """(Re)create all tables from schema.sql on a standalone connection."""
    conn = _configure(sqlite3.connect(DB_PATH))
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()
    conn.close()


def reset_db():
    """Delete the database file so seed.py can build it from scratch."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
