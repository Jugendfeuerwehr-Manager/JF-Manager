"""
Settings Manager REST API
Modern DRF-based API for application settings management
"""

from .viewsets import EmailTemplateViewSet, LDAPDepartmentMappingViewSet, OIDCGroupMappingViewSet, SettingsViewSet

__all__ = ["EmailTemplateViewSet", "LDAPDepartmentMappingViewSet", "OIDCGroupMappingViewSet", "SettingsViewSet"]
