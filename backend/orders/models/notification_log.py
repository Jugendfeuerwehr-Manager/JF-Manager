from django.db import models
from django.utils import timezone


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
    
    # Related objects - use string references to avoid circular imports
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bestellung")
    order_item = models.ForeignKey('OrderItem', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bestellartikel")
    
    # Metadata
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gesendet am")
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Benachrichtigungsprotokoll"
        verbose_name_plural = "Benachrichtigungsprotokolle"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} an {self.recipient_email} - {self.get_status_display()}"
    
    def mark_as_sent(self):
        """Mark notification as successfully sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_message):
        """Mark notification as failed with error message"""
        self.status = 'failed'
        self.error_message = error_message
        self.save()
