from django.db import models


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
