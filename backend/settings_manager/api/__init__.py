"""
Settings Manager REST API
Modern DRF-based API for application settings management
"""

from .viewsets import (
    EmailLayoutTemplateViewSet,
    EmailTemplateViewSet,
    LDAPDepartmentMappingViewSet,
    OIDCGroupMappingViewSet,
    SettingsViewSet,
)

__all__ = [
    "EmailLayoutTemplateViewSet",
    "EmailTemplateViewSet",
    "LDAPDepartmentMappingViewSet",
    "OIDCGroupMappingViewSet",
    "SettingsViewSet",
]
