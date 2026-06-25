"""
profile_service.py - shared "edit my own account" logic.

Both the customer account page and the barber profile page let a logged-in user
update their own details (name / email / phone) and change their password with
exactly the same validation rules. That logic lives here once so the two View
routes can call it without duplication; each route stays behind its own role
check and only ever passes in its own `current_user()`, so a user can only edit
their own account.
"""

import re

from flask import request, flash

from model import User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 6


def apply_account_update(user):
    """Process a profile form POST for `user`, validating and persisting.

    The form's hidden `form` field selects which form was submitted:
      * "password" -> change password (current + new + confirm)
      * anything else (details) -> update name / email / phone

    Flashes success/error messages. The caller redirects back to the page
    afterwards (persisted values reload from the DB). Returns True on a saved
    change, False if validation failed.
    """
    if request.form.get("form") == "password":
        return _change_password(user)
    return _update_details(user)


def _update_details(user):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()

    errors = []
    if not name:
        errors.append("Please enter your name.")
    if not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")
    elif User.email_taken_by_other(email, user.id):
        errors.append("That email is already in use by another account.")

    if errors:
        for e in errors:
            flash(e, "error")
        return False

    user.update_account(name, email, phone)
    flash("Your details have been updated.", "success")
    return True


def _change_password(user):
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    errors = []
    if not user.check_password(current):
        errors.append("Your current password is incorrect.")
    if len(new) < MIN_PASSWORD_LEN:
        errors.append(f"New password must be at least {MIN_PASSWORD_LEN} "
                      "characters.")
    if new != confirm:
        errors.append("New passwords do not match.")

    if errors:
        for e in errors:
            flash(e, "error")
        return False

    user.change_password(new)
    flash("Your password has been changed.", "success")
    return True
