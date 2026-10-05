"""Authentication throttles shared by session login and password actions."""

from rest_framework.throttling import AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = "login"
    rate = "10/min"


class PasswordActionThrottle(AnonRateThrottle):
    scope = "password_action"
    rate = "5/min"

    def get_cache_key(self, request, view):
        # Apply the same limit to authenticated password-guessing attempts.
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
