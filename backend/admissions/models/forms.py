from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def empty_schema():
    return {"pages": []}


class AdmissionForm(models.Model):
    """An application form of one department. The draft is edited; applicants fill published versions."""

    class SignatureMode(models.TextChoices):
        DIGITAL = "digital", "Digital unterschreiben"
        PRINT = "print", "Ausdrucken und unterschreiben"
        BOTH = "both", "Digital unterschreiben und ausdrucken"

    department = models.ForeignKey(
        "departments.Department", on_delete=models.CASCADE, related_name="admission_forms", verbose_name="Abteilung"
    )
    title = models.CharField(max_length=200, verbose_name="Titel")
    intro = models.TextField(blank=True, verbose_name="Einleitung")
    initial_status = models.ForeignKey(
        "members.Status",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Status nach Übernahme",
    )
    signature_mode = models.CharField(
        max_length=10, choices=SignatureMode.choices, default=SignatureMode.BOTH, verbose_name="Unterschrift"
    )
    decision_body = models.CharField(max_length=100, default="Jugendausschuss", verbose_name="Entscheidungsgremium")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    draft_schema = models.JSONField(default=empty_schema, verbose_name="Entwurf")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "Aufnahmeformular"
        verbose_name_plural = "Aufnahmeformulare"
        ordering = ["title"]
        permissions = [("publish_admissionform", "Aufnahmeformulare veröffentlichen")]

    def __str__(self):
        return self.title

    @property
    def current_version(self):
        return self.versions.order_by("-version").first()


class AdmissionFormVersion(models.Model):
    """A frozen form. Text blocks and legal references are copied in when publishing."""

    form = models.ForeignKey(AdmissionForm, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField(verbose_name="Version")
    title = models.CharField(max_length=200, verbose_name="Titel")
    intro = models.TextField(blank=True, verbose_name="Einleitung")
    signature_mode = models.CharField(max_length=10, choices=AdmissionForm.SignatureMode.choices)
    schema = models.JSONField(verbose_name="Formular")
    schema_hash = models.CharField(max_length=64, verbose_name="Prüfsumme")
    change_note = models.CharField(max_length=300, blank=True, verbose_name="Änderungshinweis")
    published_at = models.DateTimeField(auto_now_add=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "Formularversion"
        verbose_name_plural = "Formularversionen"
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["form", "version"], name="admissions_unique_form_version")]

    def __str__(self):
        return f"{self.title} v{self.version}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Veröffentlichte Formularversionen sind unveränderlich.")
        super().save(*args, **kwargs)


class AdmissionTextBlock(models.Model):
    """Reusable text (declarations, hints) for application forms."""

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="admission_text_blocks",
        verbose_name="Abteilung",
    )
    title = models.CharField(max_length=200, verbose_name="Titel")
    body = models.TextField(verbose_name="Text")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Textbaustein"
        verbose_name_plural = "Textbausteine"
        ordering = ["title"]

    def __str__(self):
        return self.title
