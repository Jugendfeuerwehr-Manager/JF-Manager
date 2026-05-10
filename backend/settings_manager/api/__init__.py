"""
Settings Manager REST API
Modern DRF-based API for application settings management
"""

from .viewsets import EmailTemplateViewSet, LDAPDepartmentMappingViewSet, SettingsViewSet

__all__ = ["EmailTemplateViewSet", "LDAPDepartmentMappingViewSet", "SettingsViewSet"]
