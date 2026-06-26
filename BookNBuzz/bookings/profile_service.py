"""
bookings/profile_service.py - shared "edit my own account" logic.

Both the customer account page and the barber profile page let a logged-in user
update their own details (name / email / phone) and change their password with
exactly the same validation rules. That logic lives here once so the two views
can call it without duplication; each view stays behind its own role check and
only ever passes in its own request.user, so a user can only edit their own
account.
"""

import re

from django.contrib import messages

from .models import User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 6


def apply_account_update(request):
    """Process a profile form POST for request.user, validating and persisting.

    The form's hidden `form` field selects which form was submitted:
      * "password" -> change password (current + new + confirm)
      * anything else (details) -> update name / email / phone

    Flashes success/error messages. Returns True on a saved change, False if
    validation failed.
    """
    if request.POST.get("form") == "password":
        return _change_password(request)
    return _update_details(request)


def _update_details(request):
    user = request.user
    name = request.POST.get("name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    phone = request.POST.get("phone", "").strip()

    errors = []
    if not name:
        errors.append("Please enter your name.")
    if not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")
    elif User.objects.filter(email=email).exclude(pk=user.pk).exists():
        errors.append("That email is already in use by another account.")

    if errors:
        for e in errors:
            messages.error(request, e)
        return False

    user.name, user.email, user.phone = name, email, phone
    user.save(update_fields=["name", "email", "phone"])
    messages.success(request, "Your details have been updated.")
    return True


def _change_password(request):
    user = request.user
    current = request.POST.get("current_password", "")
    new = request.POST.get("new_password", "")
    confirm = request.POST.get("confirm_password", "")

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
            messages.error(request, e)
        return False

    user.set_password(new)
    user.save(update_fields=["password"])
    # Changing the password rotates the session hash; keep the user logged in.
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, user)
    messages.success(request, "Your password has been changed.")
    return True
