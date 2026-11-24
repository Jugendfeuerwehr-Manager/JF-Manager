from django.core.validators import RegexValidator
from django.db import models


class MemberFieldDefinition(models.Model):
    """An additional member field the organisation or a department defines.

    Values live in ``Member.extra_fields`` under ``key``; application forms fill them
    through the target ``member.extra.<key>``.
    """

    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        TEXTAREA = "textarea", "Mehrzeiliger Text"
        NUMBER = "number", "Zahl"
        DATE = "date", "Datum"
        SELECT = "select", "Auswahl"
        CHECKBOX = "checkbox", "Ja / Nein"

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="member_field_definitions",
        verbose_name="Abteilung",
        help_text="Leer: gilt für die ganze Organisation.",
    )
    key = models.CharField(
        max_length=50,
        unique=True,
        validators=[RegexValidator(r"^[a-z][a-z0-9_]{0,49}$", "Kleinbuchstaben, Ziffern und _.")],
        verbose_name="Kennung",
    )
    label = models.CharField(max_length=100, verbose_name="Bezeichnung")
    field_type = models.CharField(max_length=10, choices=FieldType.choices, default=FieldType.TEXT, verbose_name="Art")
    options = models.JSONField(default=list, blank=True, verbose_name="Möglichkeiten")
    help_text = models.CharField(max_length=200, blank=True, verbose_name="Hinweis")
    position = models.PositiveIntegerField(default=0, verbose_name="Reihenfolge")
    active = models.BooleanField(default=True, verbose_name="Aktiv")

    class Meta:
        verbose_name = "Zusatzfeld"
        verbose_name_plural = "Zusatzfelder"
        ordering = ["position", "label"]

    def __str__(self):
        return self.label
