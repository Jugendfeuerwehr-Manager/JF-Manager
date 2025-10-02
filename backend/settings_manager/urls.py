from django.urls import path
from .views import (
    TabbedSettingsView,
    GeneralSettingsView,
    EmailSettingsView,
    MemberSettingsView,
    ServiceSettingsView,
    OrderSettingsView
)

app_name = 'settings_manager'

urlpatterns = [
    # Tab-Layout (Haupt-Einstellungsseite)
    path('', TabbedSettingsView.as_view(), name='overview'),
    path('tabs/', TabbedSettingsView.as_view(), name='tabbed'),
    
    # Einzelne Einstellungskategorien (für Rückwärtskompatibilität)
    path('allgemein/', GeneralSettingsView.as_view(), name='general'),
    path('email/', EmailSettingsView.as_view(), name='email'),
    path('mitglieder/', MemberSettingsView.as_view(), name='members'),
    path('dienste/', ServiceSettingsView.as_view(), name='services'),
    path('bestellungen/', OrderSettingsView.as_view(), name='orders'),
]