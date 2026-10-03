"""Isolated local demonstration. Start through backend/demo.py only."""
import os

from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ["JF_DEMO_DATABASE"]}}
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
WEB_PUSH_PUBLIC_KEY = ""
WEB_PUSH_PRIVATE_KEY = ""
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
MEDIA_ROOT = os.path.join(os.path.dirname(os.environ["JF_DEMO_DATABASE"]), "uploads")
