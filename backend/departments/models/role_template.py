from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

VALID_ROLE_SCOPES = ("organization", "department", "both")


class RoleTemplate(models.Model):
    """Descriptive metadata for a Django group, without separate permissions."""

    class Scope(models.TextChoices):
        ORGANIZATION = "organization", "Organisation"
        DEPARTMENT = "department", "Abteilung"
        BOTH = "both", "Organisation und Abteilung"

    key = models.SlugField(
        max_length=100,
        unique=True,
        validators=[RegexValidator(r"^[a-z][a-z0-9_]*$", "Nur Kleinbuchstaben, Ziffern und Unterstriche erlaubt.")],
        verbose_name="Stabiler Vorlagenschlüssel",
    )
    group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="role_template",
        verbose_name="Django-Gruppe",
    )
    name = models.CharField(max_length=200, verbose_name="Anzeigename")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    template_version = models.PositiveIntegerField(default=1, verbose_name="Vorlagenversion")
    scope = models.CharField(max_length=20, choices=Scope.choices, verbose_name="Zulässiger Bereich")
    is_delegable = models.BooleanField(default=False, verbose_name="Delegierbar nach Freigabe")
    is_archived = models.BooleanField(default=False, verbose_name="Archiviert")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Rollenvorlage"
        verbose_name_plural = "Rollenvorlagen"
        ordering = ["name", "key"]
        constraints = [
            models.CheckConstraint(check=models.Q(template_version__gte=1), name="role_template_version_gte_1"),
            models.CheckConstraint(
                check=models.Q(scope__in=VALID_ROLE_SCOPES),
                name="role_template_valid_scope",
            ),
        ]

    def clean(self):
        super().clean()
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(key=self.key).exists():
            raise ValidationError({"key": "Der Vorlagenschlüssel darf nach der Anlage nicht geändert werden."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
