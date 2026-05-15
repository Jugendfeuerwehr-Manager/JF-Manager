from django.db import models


class EmailTemplate(models.Model):
    """Customizable email templates"""

    TEMPLATE_TYPES = [
        # Current template types (used by new system)
        ("order_created", "Bestellung erstellt"),
        ("status_update", "Status geändert"),
        ("bulk_update", "Massenänderung"),
        ("pending_reminder", "Erinnerung"),
        ("daily_summary", "Tägliche Zusammenfassung"),
        ("weekly_report", "Wöchentlicher Bericht"),
        ("password_reset", "Passwort zurücksetzen"),
        ("ext_auth_pw_info", "Externer Benutzer – Passworthinweis"),
        # Legacy template types (for backward compatibility)
        ("order_confirmed", "Bestellung bestätigt (Legacy)"),
        ("order_shipped", "Bestellung versandt (Legacy)"),
        ("order_cancelled", "Bestellung storniert (Legacy)"),
        ("order_summary", "Bestellübersicht (Legacy)"),
    ]

    LAYOUT_CHOICES = [
        ("none", "Kein Layout (reines HTML)"),
        ("general", "Allgemeine Information"),
        ("important", "Wichtige Mitteilung"),
        ("events", "Veranstaltung / Termin"),
    ]

    name = models.CharField(max_length=100, verbose_name="Name")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, unique=True, verbose_name="Typ")
    subject_template = models.CharField(max_length=255, verbose_name="Betreff-Vorlage")
    html_template = models.TextField(verbose_name="HTML-Vorlage")
    text_template = models.TextField(blank=True, verbose_name="Text-Vorlage")
    layout = models.CharField(
        max_length=20,
        choices=LAYOUT_CHOICES,
        default="none",
        verbose_name="Layout",
        help_text="Layout-Vorlage, in die der HTML-Inhalt eingebettet wird.",
    )

    is_active = models.BooleanField(default=True, verbose_name="Aktiv")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "E-Mail-Vorlage"
        verbose_name_plural = "E-Mail-Vorlagen"

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
