"""Signals other apps can connect to (NOTIF-01); nothing is delivered from here."""

from django.dispatch import Signal

# Sent with ``session`` once a planned service became published (and so registrable), after commit.
session_published = Signal()
