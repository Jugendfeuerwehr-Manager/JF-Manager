import re
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import include, path, re_path
from django.utils.http import url_has_allowed_host_and_scheme

# Swagger/OpenAPI documentation
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from members.attachment_links import attachment_preview, deny_direct_attachments
from users.device_views import DeviceListView, DeviceRevokeOthersView, DeviceRevokeView
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
)
from users.session_views import SessionLoginView, SessionLogoutView, SessionMFAView, SessionStatusView

# Import custom email admin
from .api_views import AppSettingsView, PublicBrandingView
from .csp_report import csp_report
from .private_media import private_media
from .rest_urls import api

api_patterns = [
    path("api/v1/private-media/<str:kind>/<int:pk>/", private_media, name="private-media"),
    path("api/v1/security/csp-report/", csp_report, name="csp-report"),
    path("api/v1/attachment-preview/<int:pk>/<str:token>/", attachment_preview, name="attachment-preview"),
    path("api/v1/push/", include("notifications.urls")),
    path("api/v1/", include(api.urls)),
    # Browser session endpoints
    path("api/v1/auth/session/", SessionStatusView.as_view(), name="session-status"),
    path("api/v1/auth/session/login/", SessionLoginView.as_view(), name="session-login"),
    path("api/v1/auth/session/logout/", SessionLogoutView.as_view(), name="session-logout"),
    path("api/v1/auth/session/mfa/", SessionMFAView.as_view(), name="session-mfa"),
    path("api/v1/auth/reauthenticate/", ReauthenticateView.as_view(), name="reauthenticate"),
    path("api/v1/auth/devices/", DeviceListView.as_view(), name="devices"),
    path("api/v1/auth/devices/revoke-others/", DeviceRevokeOthersView.as_view(), name="devices-revoke-others"),
    path("api/v1/auth/devices/<int:pk>/revoke/", DeviceRevokeView.as_view(), name="device-revoke"),
    path("api/v1/auth/mfa/", MFAStatusView.as_view(), name="mfa-status"),
    path("api/v1/auth/mfa/setup/", MFASetupView.as_view(), name="mfa-setup"),
    path("api/v1/auth/mfa/confirm/", MFAConfirmView.as_view(), name="mfa-confirm"),
    path("api/v1/auth/mfa/recovery-codes/", MFARecoveryCodesView.as_view(), name="mfa-recovery-codes"),
    path("api/v1/auth/mfa/disable/", MFADisableView.as_view(), name="mfa-disable"),
    # OIDC Authentication endpoints
    path("api/v1/auth/oidc/public-config/", OIDCPublicConfigView.as_view(), name="oidc-public-config"),
    path("api/v1/auth/oidc/login/", OIDCLoginView.as_view(), name="oidc-login"),
    path("api/v1/auth/oidc/callback/", OIDCCallbackView.as_view(), name="oidc-callback"),
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


def central_login_redirect(request, extra_context=None):
    """Every login form uses the SPA so throttling and MFA apply uniformly."""
    next_path = request.GET.get("next", "/admin/")
    if not url_has_allowed_host_and_scheme(next_path, allowed_hosts=None) or not next_path.startswith("/"):
        next_path = "/admin/"
    return HttpResponseRedirect(f"{settings.FRONTEND_URL.rstrip('/')}/login?{urlencode({'next': next_path})}")


admin.site.login = central_login_redirect

# Authentication & Admin URLs
auth_patterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", central_login_redirect),
    path("api-auth/login/", central_login_redirect),
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
