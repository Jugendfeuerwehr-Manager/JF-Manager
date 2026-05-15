from django.conf import settings
from django.db import models


class ComposeTemplate(models.Model):
    """
    Reusable email templates for composing member emails.

    Users can save frequently used email subjects and bodies as templates
    and load them when composing a new member email.
    """

    name = models.CharField(max_length=200, verbose_name="Vorlagenname")
    subject = models.CharField(max_length=500, verbose_name="Betreff")
    body_html = models.TextField(verbose_name="Nachricht (HTML)")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Abteilung",
        related_name="compose_templates",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Erstellt von",
        related_name="compose_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "E-Mail-Vorlage"
        verbose_name_plural = "E-Mail-Vorlagen"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["department", "is_active"]),
        ]

    def __str__(self):
        return self.name
