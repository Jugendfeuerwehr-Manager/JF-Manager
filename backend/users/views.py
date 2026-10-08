"""Compatibility import; all user API routes share the secured implementation."""

from .api_views import UserViewSet

__all__ = ["UserViewSet"]
