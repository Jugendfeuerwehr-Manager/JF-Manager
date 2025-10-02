from django.db import models
from users.models import CustomUser


class NotificationPreference(models.Model):
    """User preferences for order notifications"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notification settings
    email_new_orders = models.BooleanField(default=True, verbose_name="Neue Bestellungen")
    email_status_updates = models.BooleanField(default=True, verbose_name="Status-Änderungen")
    email_bulk_updates = models.BooleanField(default=False, verbose_name="Massenänderungen")
    email_pending_reminders = models.BooleanField(default=False, verbose_name="Erinnerungen für offene Artikel")
    
    # Admin-only notifications
    email_daily_summary = models.BooleanField(default=False, verbose_name="Tägliche Zusammenfassung")
    email_weekly_report = models.BooleanField(default=False, verbose_name="Wöchentlicher Bericht")
    
    # Frequency settings
    reminder_frequency_days = models.PositiveIntegerField(default=7, verbose_name="Erinnerungs-Intervall (Tage)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Benachrichtigungseinstellung"
        verbose_name_plural = "Benachrichtigungseinstellungen"
    
    def __str__(self):
        return f"Einstellungen für {self.user.get_full_name()}"
