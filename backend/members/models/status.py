from colorfield.fields import ColorField
from django.db import models

DEFAULT_COLOR = "#FF0000"


class Status(models.Model):
    """A membership stage. Departments name their own stages; reports rely on the fixed category."""

    class Category(models.TextChoices):
        APPLICANT = "applicant", "Antrag"
        TRIAL = "trial", "Probezeit / Anwärter"
        ACTIVE = "active", "Aktiv"
        PASSIVE = "passive", "Passiv"
        LEFT = "left", "Ausgetreten"
        TRANSFERRED = "transferred", "Übergetreten"

    class Meta:
        verbose_name = "Status"
        verbose_name_plural = "Status"
        ordering = ["sort_order", "name"]

    name = models.CharField(max_length=200, default="", verbose_name="Mitgliedschaftsstatus")
    color = ColorField(default=DEFAULT_COLOR)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.ACTIVE, verbose_name="Kategorie"
    )
    # NULL: central stage, visible to every department, editable organisation-wide only.
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Abteilung",
        related_name="member_statuses",
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Reihenfolge")

    def __str__(self):
        return self.name
