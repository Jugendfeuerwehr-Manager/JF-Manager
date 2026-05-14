from django.conf import settings
from django.contrib import admin
from django.urls import include, path

# Swagger/OpenAPI documentation
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.authtoken import views

# API URLs
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# OIDC auth views
from users.oidc_views import (
    OIDCCallbackView,
    OIDCLoginView,
    OIDCPublicConfigView,
    OIDCTokenExchangeView,
)

# Import custom email admin
from .api_views import AppSettingsView, PublicBrandingView
from .rest_urls import api

api_patterns = [
    path("api/v1/", include(api.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api-token-auth/", views.obtain_auth_token),
    # JWT Authentication endpoints
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
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

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
