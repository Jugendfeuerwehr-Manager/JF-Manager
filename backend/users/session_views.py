"""Cookie-based browser sessions: status, login and server-side logout.

Browsers never receive access tokens. Every endpoint enforces CSRF, including
anonymous login, so a foreign site cannot log a victim into another account.
"""

import hashlib
import time

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from users.auth_security import LoginThrottle
from users.mfa import mark_mfa_verified, verify_second_factor
from users.mfa_policy import is_mfa_verified, mfa_state
from users.session_auth import SessionAuthentication
from users.session_policy import isoformat, session_deadlines

GENERIC_LOGIN_ERROR = "Benutzername oder Passwort ist falsch."
PENDING_KEY = "_mfa_pending_login"
PENDING_MAX_AGE = 300
PENDING_MAX_ATTEMPTS = 5


class LoginUsernameThrottle(SimpleRateThrottle):
    """Limit guessing against one account independently of the client address."""

    scope = "login_username"
    rate = "20/hour"

    def get_cache_key(self, request, view):
        username = str(request.data.get("username", "")).strip().lower()
        if not username:
            return None
        digest = hashlib.sha256(username.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}


class SessionLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(max_length=4096, trim_whitespace=False, style={"input_type": "password"})


def _pending(session):
    pending = session.get(PENDING_KEY)
    if pending and time.time() - pending["started_at"] <= PENDING_MAX_AGE:
        return pending
    return None


def session_status(request):
    user = request.user
    authenticated = bool(user and user.is_authenticated)
    data = {"authenticated": authenticated}
    if not authenticated and _pending(request.session):
        data["mfa_required"] = True
    if authenticated and not is_mfa_verified(request.session) and mfa_state(user) == "enrol":
        data["mfa_setup_required"] = True
    deadlines = session_deadlines(request.session) if authenticated else None
    if deadlines:
        data["idle_expires_at"] = isoformat(deadlines["idle_expires_at"])
        data["absolute_expires_at"] = isoformat(deadlines["absolute_expires_at"])
        data["idle_timeout_seconds"] = settings.SESSION_IDLE_TIMEOUT_SECONDS
    return data


def begin_login(request, user, *, mfa_satisfied=False):
    """Log in directly or park the user until the second factor is verified.

    ``request`` is the Django request. A user with an authenticator never gets a
    session before the code is checked; ``mfa_satisfied`` is only for an
    explicitly trusted identity provider that already verified MFA.
    """
    if mfa_state(user) == "verify" and not mfa_satisfied:
        logout(request)
        request.session.cycle_key()
        request.session[PENDING_KEY] = {
            "user_id": user.pk,
            "backend": user.backend,
            "started_at": int(time.time()),
            "attempts": 0,
        }
        return
    # login() rotates the session key and the CSRF token.
    login(request, user)
    if mfa_satisfied:
        mark_mfa_verified(request)


class SessionCsrfMixin:
    """Run Django's CSRF check even though DRF marks API views as exempt."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class SessionStatusView(APIView):
    """GET /api/v1/auth/session/ — current state and a fresh CSRF cookie."""

    permission_classes = [AllowAny]
    authentication_classes = [SessionAuthentication]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response(session_status(request))


class SessionLoginView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/login/ — establish a rotated session cookie."""

    throttle_classes = [LoginThrottle, LoginUsernameThrottle]

    def post(self, request):
        serializer = SessionLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request._request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            return Response({"detail": GENERIC_LOGIN_ERROR}, status=status.HTTP_401_UNAUTHORIZED)
        begin_login(request._request, user)
        return Response(session_status(request._request))


class MFACodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)


class SessionMFAView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/mfa/ — finish a login with TOTP or recovery code."""

    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = MFACodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = request._request.session
        pending = _pending(session)
        if pending is None:
            session.pop(PENDING_KEY, None)
            return Response(
                {"detail": "Die Anmeldung ist abgelaufen. Bitte erneut anmelden.", "code": "mfa_login_expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = get_user_model().objects.filter(pk=pending["user_id"], is_active=True).first()
        if user is None or not verify_second_factor(user, serializer.validated_data["code"]):
            pending["attempts"] += 1
            if pending["attempts"] >= PENDING_MAX_ATTEMPTS:
                session.pop(PENDING_KEY, None)
            else:
                session[PENDING_KEY] = pending
            return Response({"detail": "Der Code ist ungültig."}, status=status.HTTP_400_BAD_REQUEST)
        session.pop(PENDING_KEY, None)
        login(request._request, user, backend=pending["backend"])
        mark_mfa_verified(request._request)
        return Response(session_status(request._request))


class SessionLogoutView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/logout/ — delete the server-side session."""

    def post(self, request):
        logout(request._request)
        return Response(session_status(request._request))
