"""
Settings Manager REST API
Modern DRF-based API for application settings management
"""

from .viewsets import SettingsViewSet, EmailTemplateViewSet

__all__ = ['SettingsViewSet', 'EmailTemplateViewSet']
