"""jf_manager_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.authtoken import views

from .rest_urls import api

# API URLs
api_patterns = [
    path('api/v1/', include(api.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api-token-auth/', views.obtain_auth_token),
]

# Application URLs
app_patterns = [
    path('inventory/', include('inventory.urls')),
    path('members/', include('members.urls')),
    path('servicebook/', include('servicebook.urls')),
]

# Authentication URLs
auth_patterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
]

# Utility URLs
util_patterns = [
    path('imagefit/', include('imagefit.urls')),
    path('', RedirectView.as_view(url='/members/', permanent=False), name='home'),
]

# Health check URLs
health_patterns = [
    path('health/', include('health.urls')),
]

# Combine all URL patterns
urlpatterns = api_patterns + app_patterns + auth_patterns + util_patterns + health_patterns

# Serve media and static files in development
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
