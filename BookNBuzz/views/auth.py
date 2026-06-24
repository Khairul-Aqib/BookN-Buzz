"""
views/auth.py - authentication View blueprint.

Use cases: Register Account, Login, Logout.
"""

import re

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session)

from model import Customer, User
from auth_utils import login_user, logout_user, current_user

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------- #
#  Register Account  (Customer use case)
# --------------------------------------------------------------------------- #
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("customer.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        errors = []
        if not name:
            errors.append("Please enter your name.")
        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")
        elif User.email_exists(email):
            errors.append("That email is already registered. Try logging in.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html",
                                   form={"name": name, "email": email, "phone": phone})

        customer = Customer(name=name, email=email, phone=phone)
        customer.set_password(password)
        customer.save()
        login_user(customer)
        flash(f"Welcome to BookN'Buzz, {name}! Your account is ready.", "success")
        return redirect(url_for("customer.home"))

    return render_template("auth/register.html", form={})


# --------------------------------------------------------------------------- #
#  Login  (Customer + Barber use case)
# --------------------------------------------------------------------------- #
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("customer.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.find_by_email(email)
        if user is None or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html", form={"email": email})

        login_user(user)
        flash(f"Welcome back, {user.name}!", "success")
        if user.role == "barber":
            return redirect(url_for("barber.dashboard"))
        return redirect(url_for("customer.home"))

    return render_template("auth/login.html", form={})


# --------------------------------------------------------------------------- #
#  Logout
# --------------------------------------------------------------------------- #
@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
