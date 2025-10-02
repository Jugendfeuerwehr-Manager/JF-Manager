from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models


class SettingsCategory(models.Model):
    """
    Model to represent different settings categories for permission management
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Name')
    code = models.CharField(max_length=50, unique=True, verbose_name='Code')
    description = models.TextField(blank=True, verbose_name='Beschreibung')
    
    class Meta:
        verbose_name = 'Einstellungskategorie'
        verbose_name_plural = 'Einstellungskategorien'
        permissions = [
            ('view_general_settings', 'Kann allgemeine Einstellungen einsehen'),
            ('change_general_settings', 'Kann allgemeine Einstellungen ändern'),
            ('view_email_settings', 'Kann E-Mail Einstellungen einsehen'),
            ('change_email_settings', 'Kann E-Mail Einstellungen ändern'),
            ('view_member_settings', 'Kann Mitglieder Einstellungen einsehen'),
            ('change_member_settings', 'Kann Mitglieder Einstellungen ändern'),
            ('view_service_settings', 'Kann Dienst Einstellungen einsehen'),
            ('change_service_settings', 'Kann Dienst Einstellungen ändern'),
            ('view_order_settings', 'Kann Bestell Einstellungen einsehen'),
            ('change_order_settings', 'Kann Bestell Einstellungen ändern'),
            ('view_all_settings', 'Kann alle Einstellungen einsehen'),
            ('change_all_settings', 'Kann alle Einstellungen ändern'),
        ]
    
    def __str__(self):
        return self.name