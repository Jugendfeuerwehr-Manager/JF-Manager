import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def application_file_path(instance, filename):
    return f"admissions/{instance.application_id}/{uuid.uuid4().hex}.{filename.rsplit('.', 1)[-1]}"


class Application(models.Model):
    """A submitted application. Answers and files are sealed and never change afterwards."""

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Eingegangen"
        APPROVED = "approved", "Angenommen"
        REJECTED = "rejected", "Abgelehnt"
        DEFERRED = "deferred", "Zurückgestellt"
        WITHDRAWN = "withdrawn", "Zurückgezogen"
        TAKEN_OVER = "taken_over", "Übernommen"

    OPEN_STATUSES = (Status.SUBMITTED, Status.DEFERRED)

    form_version = models.ForeignKey(
        "admissions.AdmissionFormVersion", on_delete=models.PROTECT, related_name="applications"
    )
    department = models.ForeignKey("departments.Department", on_delete=models.CASCADE, related_name="applications")
    voucher = models.OneToOneField(
        "admissions.AdmissionVoucher", on_delete=models.SET_NULL, null=True, blank=True, related_name="application"
    )
    answers = models.JSONField(verbose_name="Antworten")
    applicant_name = models.CharField(max_length=300, verbose_name="Antragsteller*in")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, verbose_name="Status")
    submitted_at = models.DateTimeField(verbose_name="Eingereicht am")
    member = models.ForeignKey(
        "members.Member", on_delete=models.SET_NULL, null=True, blank=True, related_name="applications"
    )
    taken_over_at = models.DateTimeField(null=True, blank=True)
    taken_over_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    SEALED_FIELDS = ("form_version_id", "department_id", "answers", "applicant_name", "submitted_at")

    class Meta:
        verbose_name = "Aufnahmeantrag"
        verbose_name_plural = "Aufnahmeanträge"
        ordering = ["-submitted_at"]
        permissions = [
            ("record_decision", "Beschlüsse zu Aufnahmeanträgen erfassen"),
            ("take_over_application", "Aufnahmeanträge in die Mitgliederverwaltung übernehmen"),
            ("export_application", "Aufnahmeanträge exportieren"),
        ]

    def __str__(self):
        return f"{self.applicant_name} ({self.submitted_at:%d.%m.%Y})"

    def save(self, *args, **kwargs):
        # Sealed content: once stored, only status and takeover fields may change.
        if self.pk is not None:
            stored = type(self).objects.filter(pk=self.pk).values(*self.SEALED_FIELDS).first()
            current = {field: getattr(self, field) for field in self.SEALED_FIELDS}
            if stored is not None and stored != current:
                raise ValidationError("Der Inhalt eines eingereichten Antrags ist versiegelt.")
        super().save(*args, **kwargs)


class ApplicationFile(models.Model):
    """Photo or signature of an application; the SHA-256 is part of the seal."""

    class Kind(models.TextChoices):
        PHOTO = "photo", "Passbild"
        SIGNATURE = "signature", "Unterschrift"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="files")
    key = models.CharField(max_length=50, verbose_name="Kennung")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    file = models.FileField(upload_to=application_file_path)
    sha256 = models.CharField(max_length=64)

    class Meta:
        verbose_name = "Antragsdatei"
        verbose_name_plural = "Antragsdateien"
        constraints = [models.UniqueConstraint(fields=["application", "key"], name="admissions_unique_file_key")]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Dateien eines eingereichten Antrags sind versiegelt.")
        super().save(*args, **kwargs)
