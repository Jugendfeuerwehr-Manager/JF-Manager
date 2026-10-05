import re
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

# Swagger/OpenAPI documentation
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# API URLs
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from members.attachment_links import attachment_preview, deny_direct_attachments
from users.auth_security import SecureObtainAuthToken, SecureTokenObtainPairView
from users.mfa_views import (
    MFAConfirmView,
    MFADisableView,
    MFARecoveryCodesView,
    MFASetupView,
    MFAStatusView,
    ReauthenticateView,
)

# OIDC auth views
from users.oidc_views import (
    OIDCCallbackView,
    OIDCLoginView,
    OIDCPublicConfigView,
    OIDCTokenExchangeView,
)
from users.session_views import SessionLoginView, SessionLogoutView, SessionStatusView

# Import custom email admin
from .api_views import AppSettingsView, PublicBrandingView
from .private_media import private_media
from .rest_urls import api

api_patterns = [
    path("api/v1/private-media/<str:kind>/<int:pk>/", private_media, name="private-media"),
    path("api/v1/attachment-preview/<int:pk>/<str:token>/", attachment_preview, name="attachment-preview"),
    path("api/v1/push/", include("notifications.urls")),
    path("api/v1/", include(api.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api-token-auth/", SecureObtainAuthToken.as_view()),
    # Browser session endpoints
    path("api/v1/auth/session/", SessionStatusView.as_view(), name="session-status"),
    path("api/v1/auth/session/login/", SessionLoginView.as_view(), name="session-login"),
    path("api/v1/auth/session/logout/", SessionLogoutView.as_view(), name="session-logout"),
    path("api/v1/auth/reauthenticate/", ReauthenticateView.as_view(), name="reauthenticate"),
    path("api/v1/auth/mfa/", MFAStatusView.as_view(), name="mfa-status"),
    path("api/v1/auth/mfa/setup/", MFASetupView.as_view(), name="mfa-setup"),
    path("api/v1/auth/mfa/confirm/", MFAConfirmView.as_view(), name="mfa-confirm"),
    path("api/v1/auth/mfa/recovery-codes/", MFARecoveryCodesView.as_view(), name="mfa-recovery-codes"),
    path("api/v1/auth/mfa/disable/", MFADisableView.as_view(), name="mfa-disable"),
    # JWT Authentication endpoints
    path("api/v1/auth/login/", SecureTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # OIDC Authentication endpoints
    path("api/v1/auth/oidc/public-config/", OIDCPublicConfigView.as_view(), name="oidc-public-config"),
    path("api/v1/auth/oidc/login/", OIDCLoginView.as_view(), name="oidc-login"),
    path("api/v1/auth/oidc/callback/", OIDCCallbackView.as_view(), name="oidc-callback"),
    path("api/v1/auth/oidc/exchange/", OIDCTokenExchangeView.as_view(), name="oidc-exchange"),
    # User info
    path("api/v1/userinfo/", AppSettingsView.as_view(), name="userinfo"),
    # App settings
    path("api/v1/settings/", AppSettingsView.as_view(), name="app-settings"),
    # Public branding info (no auth required)
    path("api/v1/app/branding/", PublicBrandingView.as_view(), name="public-branding"),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Authentication & Admin URLs
auth_patterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
]

# Health check URLs
health_patterns = [
    path("health/", include("health.urls")),
]

# Combine all URL patterns
urlpatterns = api_patterns + auth_patterns + health_patterns

# Serve media and static files in development
if settings.DEBUG:
    from django.conf.urls.static import static

    media_path = urlsplit(settings.MEDIA_URL).path.lstrip("/")
    urlpatterns += [re_path(r"^" + re.escape(media_path), deny_direct_attachments)]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
