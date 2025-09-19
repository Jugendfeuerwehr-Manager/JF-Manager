"""
Settings Manager views package.
Provides view classes for managing Django dynamic preferences with permission controls.
"""

from .base_views import BaseSettingsFormView
from .category_views import (
    GeneralSettingsView,
    EmailSettingsView,
    MemberSettingsView,
    ServiceSettingsView,
    OrderSettingsView
)
from .tabbed_view import TabbedSettingsView

__all__ = [
    'BaseSettingsFormView',
    'GeneralSettingsView',
    'EmailSettingsView',
    'MemberSettingsView',
    'ServiceSettingsView',
    'OrderSettingsView',
    'TabbedSettingsView',
]