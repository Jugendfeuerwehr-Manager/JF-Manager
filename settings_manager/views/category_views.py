from .base_views import BaseSettingsFormView
from ..forms import (
    GeneralSettingsForm,
    EmailSettingsForm,
    MemberSettingsForm,
    ServiceSettingsForm,
    OrderSettingsForm
)


class GeneralSettingsView(BaseSettingsFormView):
    """
    View für allgemeine Einstellungen
    """
    form_class = GeneralSettingsForm
    category_code = 'general'
    category_title = 'Allgemeine Einstellungen'


class EmailSettingsView(BaseSettingsFormView):
    """
    View für E-Mail Einstellungen
    """
    form_class = EmailSettingsForm
    category_code = 'email'
    category_title = 'E-Mail Einstellungen'


class MemberSettingsView(BaseSettingsFormView):
    """
    View für Mitglieder Einstellungen
    """
    form_class = MemberSettingsForm
    category_code = 'member'
    category_title = 'Mitglieder Einstellungen'


class ServiceSettingsView(BaseSettingsFormView):
    """
    View für Dienst Einstellungen
    """
    form_class = ServiceSettingsForm
    category_code = 'service'
    category_title = 'Dienst Einstellungen'


class OrderSettingsView(BaseSettingsFormView):
    """
    View für Bestell Einstellungen
    """
    form_class = OrderSettingsForm
    category_code = 'order'
    category_title = 'Bestell Einstellungen'