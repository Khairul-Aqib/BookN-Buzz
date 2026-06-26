"""WSGI config for the booknbuzz project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "booknbuzz.settings")

application = get_wsgi_application()
