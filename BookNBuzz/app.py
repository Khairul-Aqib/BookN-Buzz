"""
app.py - application entry point.

Creates the Flask app, wires up the database, registers the three View
blueprints (auth / customer / barber) and exposes a couple of template
helpers. Run with:  python app.py  -> http://localhost:5000
"""

from flask import Flask, redirect, url_for

import db
from auth_utils import current_user
from model import MOBILE_SERVICE_FEE
from views.auth import auth_bp
from views.customer import customer_bp
from views.barber import barber_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "booknbuzz-dev-secret-change-me"

    # Database teardown handling.
    db.init_app(app)

    # Register the View layer (blueprints).
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(barber_bp)

    # Landing page -> packages browser.
    @app.route("/")
    def index():
        return redirect(url_for("customer.home"))

    # Make the current user + unread notification count available to every
    # template (used by the nav bar).
    @app.context_processor
    def inject_user():
        user = current_user()
        unread = 0
        if user is not None and user.role == "customer":
            unread = user.unread_count()
        return {"current_user": user, "unread_count": unread,
                "mobile_fee": MOBILE_SERVICE_FEE}

    # Pretty currency filter used across templates.
    @app.template_filter("money")
    def money(value):
        try:
            return f"RM{float(value):.2f}"
        except (TypeError, ValueError):
            return "RM0.00"

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
