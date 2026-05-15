from django.db import models


class EmailLayoutTemplate(models.Model):
    """
    Custom override for the HTML layout wrapper templates.

    If a record exists for a given layout_type, it takes precedence
    over the static file in templates/email_layouts/{layout_type}.html.
    This allows admins to customise the visual design of layout wrappers
    without touching the filesystem.
    """

    LAYOUT_CHOICES = [
        ("general", "Allgemeine Information"),
        ("important", "Wichtige Mitteilung"),
        ("events", "Veranstaltung / Termin"),
    ]

    layout_type = models.CharField(
        max_length=20,
        choices=LAYOUT_CHOICES,
        unique=True,
        verbose_name="Layout-Typ",
    )
    html_content = models.TextField(verbose_name="HTML-Inhalt")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "E-Mail-Layout-Vorlage"
        verbose_name_plural = "E-Mail-Layout-Vorlagen"

    def __str__(self) -> str:
        return f"Layout: {self.get_layout_type_display()}"
