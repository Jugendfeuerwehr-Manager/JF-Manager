"""
Settings Manager REST API
Modern DRF-based API for application settings management
"""

from .viewsets import EmailTemplateViewSet, SettingsViewSet

__all__ = ["EmailTemplateViewSet", "SettingsViewSet"]
