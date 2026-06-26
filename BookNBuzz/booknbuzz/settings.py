"""
Django settings for the BookN'Buzz project.

A single project (booknbuzz) with one app (bookings) implementing the whole
barber-shop booking system on Django's default SQLite backend.
"""

import os
from pathlib import Path

# BASE_DIR is the BookNBuzz/ folder that holds manage.py, templates/ and static/.
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
#  Core
# --------------------------------------------------------------------------- #
# Read the secret key from the environment in production; fall back to an
# explicitly-insecure throwaway value for local/dev so the app runs out of the
# box. Never use the fallback for a real deployment — set DJANGO_SECRET_KEY.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-booknbuzz-dev-secret-change-me",
)
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bookings",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "booknbuzz.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Templates live inside the app (bookings/templates/), found via APP_DIRS.
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # BookN'Buzz nav helpers: current_user, unread_count, mobile_fee.
                "bookings.context_processors.nav",
            ],
        },
    },
]

WSGI_APPLICATION = "booknbuzz.wsgi.application"

# --------------------------------------------------------------------------- #
#  Database (default SQLite)
# --------------------------------------------------------------------------- #
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "booknbuzz.db",
    }
}

# --------------------------------------------------------------------------- #
#  Auth
# --------------------------------------------------------------------------- #
AUTH_USER_MODEL = "bookings.User"
LOGIN_URL = "auth_login"
LOGIN_REDIRECT_URL = "customer_home"
LOGOUT_REDIRECT_URL = "auth_login"

# Passwords are hashed by Django; we keep the app's own >=6 char rule in the
# views, so the built-in validator list is intentionally left empty here.
AUTH_PASSWORD_VALIDATORS = []

# --------------------------------------------------------------------------- #
#  I18N / TZ
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kuala_Lumpur"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------- #
#  Static files
# --------------------------------------------------------------------------- #
STATIC_URL = "static/"
# Static assets live inside the app (bookings/static/), found by the app-dir
# static finder automatically.

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
