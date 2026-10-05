"""Cookie-based browser sessions: status, login and server-side logout.

Browsers never receive access tokens. Every endpoint enforces CSRF, including
anonymous login, so a foreign site cannot log a victim into another account.
"""

import hashlib

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from users.auth_security import LoginThrottle

GENERIC_LOGIN_ERROR = "Benutzername oder Passwort ist falsch."


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


def session_status(request):
    user = request.user
    return {"authenticated": bool(user and user.is_authenticated)}


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
        # login() rotates the session key and the CSRF token.
        login(request._request, user)
        return Response(session_status(request._request))


class SessionLogoutView(SessionCsrfMixin, APIView):
    """POST /api/v1/auth/session/logout/ — delete the server-side session."""

    def post(self, request):
        logout(request._request)
        return Response(session_status(request._request))
