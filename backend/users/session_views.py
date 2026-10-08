"""Cookie-based browser sessions: status, login and server-side logout.

Browsers never receive access tokens. Every endpoint enforces CSRF, including
anonymous login, so a foreign site cannot log a victim into another account.
"""

import hashlib
import json
import time

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from users import passkeys
from users.auth_security import LoginThrottle
from users.mfa import has_passkeys, has_totp, mark_mfa_verified, verify_second_factor
from users.mfa_policy import is_mfa_verified, mfa_state
from users.session_auth import SessionAuthentication
from users.session_policy import PRIVILEGED_KEY, isoformat, lifetimes, session_deadlines

GENERIC_LOGIN_ERROR = "Benutzername oder Passwort ist falsch."
PENDING_KEY = "_mfa_pending_login"
PENDING_MAX_AGE = 300
PENDING_MAX_ATTEMPTS = 5
# Passkey sign-ins load the account like a local login.
PASSKEY_BACKEND = "django.contrib.auth.backends.ModelBackend"


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
    pending = _pending(request.session) if not authenticated else None
    if pending:
        data["mfa_required"] = True
        pending_user = get_user_model().objects.filter(pk=pending["user_id"]).first()
        if pending_user is not None:
            # Only after a correct password: which second factors this account has.
            data["mfa_methods"] = {"totp": has_totp(pending_user), "passkey": has_passkeys(pending_user)}
    if authenticated and not is_mfa_verified(request.session) and mfa_state(user) == "enrol":
        data["mfa_setup_required"] = True
    deadlines = session_deadlines(request.session) if authenticated else None
    if deadlines:
        data["idle_expires_at"] = isoformat(deadlines["idle_expires_at"])
        data["absolute_expires_at"] = isoformat(deadlines["absolute_expires_at"])
        data["idle_timeout_seconds"] = lifetimes(request.session)[0]
        data["privileged_session"] = bool(request.session.get(PRIVILEGED_KEY))
    if authenticated:
        # The frontend routes portal accounts (parents, members) to their own area.
        data["account_kind"] = user.account_kind
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
    code = serializers.CharField(max_length=32, required=False, allow_blank=True)
    passkey = serializers.DictField(required=False)

    def validate(self, attrs):
        if not attrs.get("code") and not attrs.get("passkey"):
            raise serializers.ValidationError("Code oder Passkey erforderlich.")
        return attrs


def _expired_login():
    return Response(
        {"detail": "Die Anmeldung ist abgelaufen. Bitte erneut anmelden.", "code": "mfa_login_expired"},
        status=status.HTTP_400_BAD_REQUEST,
    )


class SessionPasskeyOptionsView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/mfa/passkey-options/ — challenge for the pending login."""

    throttle_classes = [LoginThrottle]

    def post(self, request):
        session = request._request.session
        pending = _pending(session)
        if pending is None:
            session.pop(PENDING_KEY, None)
            return _expired_login()
        user = get_user_model().objects.filter(pk=pending["user_id"], is_active=True).first()
        options = passkeys.authentication_options(session, user) if user else None
        if options is None:
            return Response(
                {"detail": "Für dieses Konto ist kein Passkey eingerichtet."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(json.loads(options))


class SessionMFAView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/mfa/ — finish a login with TOTP, recovery code or passkey."""

    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = MFACodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = request._request.session
        pending = _pending(session)
        if pending is None:
            session.pop(PENDING_KEY, None)
            return _expired_login()
        user = get_user_model().objects.filter(pk=pending["user_id"], is_active=True).first()
        if user is None or not _second_factor_ok(session, user, serializer.validated_data):
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


def _second_factor_ok(session, user, data):
    if data.get("passkey"):
        try:
            passkeys.authenticate(session, user, data["passkey"])
        except passkeys.PasskeyError:
            return False
        return True
    return verify_second_factor(user, data.get("code", ""))


class PasskeySignInSerializer(serializers.Serializer):
    passkey = serializers.DictField()


class SessionPasskeySignInOptionsView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/passkey/options/ — challenge for a sign-in without password."""

    throttle_classes = [LoginThrottle]

    def post(self, request):
        session = request._request.session
        session.pop(PENDING_KEY, None)
        return Response(json.loads(passkeys.signin_options(session)))


class SessionPasskeySignInView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/passkey/ — sign in with a passkey alone (SEC-12).

    The passkey must have verified the person (PIN or biometrics); the session
    then counts as MFA-verified. Only local accounts: LDAP and SSO accounts
    keep their directory as first factor, so a disabled directory account
    cannot sign in with a passkey.
    """

    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = PasskeySignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = request._request.session
        try:
            credential = passkeys.signin(session, serializer.validated_data["passkey"])
        except passkeys.PasskeyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        user = credential.user
        if not user.is_active:
            return Response(
                {"detail": "Der Passkey konnte nicht bestätigt werden."}, status=status.HTTP_401_UNAUTHORIZED
            )
        if user.auth_source != user.AuthSource.LOCAL:
            return Response(
                {
                    "detail": "Für dieses Konto bestätigt der Passkey nur die Anmeldung mit Passwort oder SSO.",
                    "code": "passkey_second_factor_only",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        session.pop(PENDING_KEY, None)
        login(request._request, user, backend=PASSKEY_BACKEND)
        mark_mfa_verified(request._request)
        return Response(session_status(request._request))


class SessionLogoutView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/logout/ — delete the server-side session."""

    def post(self, request):
        logout(request._request)
        return Response(session_status(request._request))
