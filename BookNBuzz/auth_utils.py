"""
auth_utils.py - session helpers and access-control decorators.

Shared by all View blueprints so route functions can require a logged-in user
(@login_required) or a barber/admin (@barber_required), and read the current
user with current_user().
"""

from functools import wraps

from flask import session, redirect, url_for, flash, g

from model import User


def current_user():
    """Return the logged-in User (Customer/Barber) or None.

    Cached on `g` so repeated calls within one request hit the DB once.
    """
    if "user_id" not in session:
        return None
    if "current_user" not in g:
        g.current_user = User.get(session["user_id"])
    return g.current_user


def login_user(user):
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role


def logout_user():
    session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def barber_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        if user.role != "barber":
            flash("That area is for barbers only.", "error")
            return redirect(url_for("customer.packages"))
        return view(*args, **kwargs)
    return wrapped
