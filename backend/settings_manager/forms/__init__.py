"""
Settings Manager forms package.
Provides form classes for managing Django dynamic preferences with different categories.
"""

from .base_form import BaseSettingsForm
from .general_form import GeneralSettingsForm
from .email_form import EmailSettingsForm
from .member_form import MemberSettingsForm
from .service_form import ServiceSettingsForm
from .order_form import OrderSettingsForm

__all__ = [
    'BaseSettingsForm',
    'GeneralSettingsForm',
    'EmailSettingsForm',
    'MemberSettingsForm',
    'ServiceSettingsForm',
    'OrderSettingsForm',
]