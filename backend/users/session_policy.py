"""Server-side idle and absolute lifetime for browser sessions.

The cookie age alone is not enough: a stolen cookie must stop working after
inactivity and after the absolute maximum, regardless of client behaviour.

Two profiles: ordinary accounts keep long-running sessions (security changes
need a fresh confirmation instead), accounts with mandatory MFA get a short one.
"""

import time
from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from users.devices import touch_device
from users.mfa import REAUTH_KEY
from users.mfa_policy import mfa_required

STARTED_KEY = "_session_started_at"
ACTIVITY_KEY = "_session_last_activity"
PRIVILEGED_KEY = "_session_privileged"
PRIVILEGE_CHECKED_KEY = "_session_privilege_checked_at"
# Role changes during a session switch the profile within this delay.
PRIVILEGE_RECHECK_INTERVAL = 300
# Avoid a session write on every request; idle expiry may lag by this much.
ACTIVITY_WRITE_INTERVAL = 30
# Status checks report the remaining time without counting as activity.
PASSIVE_PATHS = ("/api/v1/auth/session/",)


@receiver(user_logged_in)
def start_session_clock(sender, request, user, **kwargs):
    if request is None or not hasattr(request, "session"):
        return
    now = int(time.time())
    request.session[STARTED_KEY] = now
    request.session[ACTIVITY_KEY] = now
    # A completed login counts as a fresh confirmation for security changes.
    request.session[REAUTH_KEY] = now
    _apply_profile(request.session, mfa_required(user), now)


def _apply_profile(session, privileged, now):
    session[PRIVILEGED_KEY] = privileged
    session[PRIVILEGE_CHECKED_KEY] = now
    # Cookie and stored session expire with the profile's absolute limit.
    session.set_expiry(lifetimes(session)[1])


def lifetimes(session):
    """(idle, absolute) seconds for this session's profile."""
    if session.get(PRIVILEGED_KEY):
        return settings.PRIVILEGED_SESSION_IDLE_TIMEOUT_SECONDS, settings.PRIVILEGED_SESSION_MAX_AGE_SECONDS
    return settings.SESSION_IDLE_TIMEOUT_SECONDS, settings.SESSION_MAX_AGE_SECONDS


def session_deadlines(session):
    started = session.get(STARTED_KEY)
    activity = session.get(ACTIVITY_KEY)
    if started is None or activity is None:
        return None
    idle, absolute = lifetimes(session)
    return {
        "idle_expires_at": activity + idle,
        "absolute_expires_at": started + absolute,
    }


def isoformat(timestamp):
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


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
            _apply_profile(session, mfa_required(user), now)
            return
        if now - session.get(PRIVILEGE_CHECKED_KEY, 0) >= PRIVILEGE_RECHECK_INTERVAL:
            privileged = mfa_required(user)
            if privileged != bool(session.get(PRIVILEGED_KEY)):
                _apply_profile(session, privileged, now)
                deadlines = session_deadlines(session)
            else:
                session[PRIVILEGE_CHECKED_KEY] = now
        if now >= deadlines["idle_expires_at"] or now >= deadlines["absolute_expires_at"]:
            logout(request)
            return
        if request.path in PASSIVE_PATHS:
            return
        if now - session[ACTIVITY_KEY] >= ACTIVITY_WRITE_INTERVAL:
            session[ACTIVITY_KEY] = now
            touch_device(session.session_key)
