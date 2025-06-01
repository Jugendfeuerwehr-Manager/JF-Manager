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


class NotificationLog(models.Model):
    """Log of sent notifications for tracking and debugging"""
    NOTIFICATION_TYPES = [
        ('order_created', 'Bestellung erstellt'),
        ('status_update', 'Status geändert'),
        ('bulk_update', 'Massenänderung'),
        ('pending_reminder', 'Erinnerung'),
        ('daily_summary', 'Tägliche Zusammenfassung'),
        ('weekly_report', 'Wöchentlicher Bericht'),
        ('order_summary', 'Bestellübersicht für Gerätewart'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Gesendet'),
        ('failed', 'Fehlgeschlagen'),
        ('pending', 'Ausstehend'),
    ]
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name="Typ")
    recipient_email = models.EmailField(verbose_name="Empfänger")
    subject = models.CharField(max_length=255, verbose_name="Betreff")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    
    # Related objects - we'll import these models at runtime to avoid circular imports
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bestellung")
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bestellartikel")
    
    # Metadata
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gesendet am")
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")
    additional_data = models.JSONField(default=dict, blank=True, verbose_name="Zusätzliche Daten")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Benachrichtigungsprotokoll"
        verbose_name_plural = "Benachrichtigungsprotokolle"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} an {self.recipient_email} - {self.get_status_display()}"
    
    def mark_as_sent(self):
        """Mark notification as successfully sent"""
        from django.utils import timezone
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_message):
        """Mark notification as failed with error message"""
        self.status = 'failed'
        self.error_message = error_message
        self.save()


class EmailTemplate(models.Model):
    """Customizable email templates"""
    TEMPLATE_TYPES = [
        ('order_created', 'Bestellung erstellt'),
        ('status_update', 'Status geändert'),
        ('bulk_update', 'Massenänderung'),
        ('pending_reminder', 'Erinnerung'),
        ('daily_summary', 'Tägliche Zusammenfassung'),
        ('weekly_report', 'Wöchentlicher Bericht'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Name")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, unique=True, verbose_name="Typ")
    subject_template = models.CharField(max_length=255, verbose_name="Betreff-Vorlage")
    html_template = models.TextField(verbose_name="HTML-Vorlage")
    text_template = models.TextField(blank=True, verbose_name="Text-Vorlage")
    
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "E-Mail-Vorlage"
        verbose_name_plural = "E-Mail-Vorlagen"
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
