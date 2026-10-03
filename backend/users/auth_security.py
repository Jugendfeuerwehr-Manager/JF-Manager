"""Authentication throttles and password-bound refresh credentials."""

from django.contrib.auth import get_user_model
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.views import TokenObtainPairView


class LoginThrottle(AnonRateThrottle):
    scope = "login"
    rate = "10/min"


class PasswordActionThrottle(AnonRateThrottle):
    scope = "password_action"
    rate = "5/min"

    def get_cache_key(self, request, view):
        # Apply the same limit to authenticated password-guessing attempts.
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class SecureTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]


class SecureObtainAuthToken(ObtainAuthToken):
    throttle_classes = [LoginThrottle]


class SecureTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        user = get_user_model().objects.filter(pk=refresh.get(api_settings.USER_ID_CLAIM), is_active=True).first()
        if user is None or refresh.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
            raise AuthenticationFailed("Anmeldung abgelaufen. Bitte erneut anmelden.")
        return super().validate(attrs)
