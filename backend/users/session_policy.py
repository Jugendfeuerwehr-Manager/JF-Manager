"""Server-side idle and absolute lifetime for browser sessions.

The cookie age alone is not enough: a stolen cookie must stop working after
inactivity and after the absolute maximum, regardless of client behaviour.
"""

import time
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from users.mfa import REAUTH_KEY

STARTED_KEY = "_session_started_at"
ACTIVITY_KEY = "_session_last_activity"
# Avoid a session write on every request; idle expiry may lag by this much.
ACTIVITY_WRITE_INTERVAL = 30
# Status checks report the remaining time without counting as activity.
PASSIVE_PATHS = ("/api/v1/auth/session/",)


def bounded(value, minimum, maximum):
    return max(minimum, min(maximum, int(value)))


@receiver(user_logged_in)
def start_session_clock(sender, request, user, **kwargs):
    if request is None or not hasattr(request, "session"):
        return
    now = int(time.time())
    request.session[STARTED_KEY] = now
    request.session[ACTIVITY_KEY] = now
    # A completed login counts as a fresh confirmation for security changes.
    request.session[REAUTH_KEY] = now


def session_deadlines(session):
    started = session.get(STARTED_KEY)
    activity = session.get(ACTIVITY_KEY)
    if started is None or activity is None:
        return None
    return {
        "idle_expires_at": activity + settings.SESSION_IDLE_TIMEOUT_SECONDS,
        "absolute_expires_at": started + settings.SESSION_MAX_AGE_SECONDS,
    }


def isoformat(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


class SessionPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.enforce(request)
        return self.get_response(request)

    def enforce(self, request):
        session = getattr(request, "session", None)
        user = getattr(request, "user", None)
        if session is None or user is None or not user.is_authenticated:
            return
        now = int(time.time())
        deadlines = session_deadlines(session)
        if deadlines is None:
            # Sessions created outside login() (or before this policy) start now.
            session[STARTED_KEY] = session.get(STARTED_KEY, now)
            session[ACTIVITY_KEY] = now
            return
        if now >= deadlines["idle_expires_at"] or now >= deadlines["absolute_expires_at"]:
            logout(request)
            return
        if request.path in PASSIVE_PATHS:
            return
        if now - session[ACTIVITY_KEY] >= ACTIVITY_WRITE_INTERVAL:
            session[ACTIVITY_KEY] = now
