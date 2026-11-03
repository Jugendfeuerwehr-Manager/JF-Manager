import secrets

from django.core.exceptions import ValidationError
from django.db import models


def public_id():
    return secrets.token_urlsafe(9)


class Seal(models.Model):
    """A signed fingerprint of a record at one moment. Seals of one subject form a chain."""

    class Kind(models.TextChoices):
        SUBMISSION = "submission", "Antrag eingereicht"
        DECISION = "decision", "Beschluss"
        EXPORT = "export", "Export"
        ANNUAL_REPORT = "annual_report", "Jahresmeldung"

    subject_type = models.CharField(max_length=50)
    subject_id = models.PositiveBigIntegerField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    public_id = models.CharField(max_length=16, unique=True, default=public_id)
    content_hash = models.CharField(max_length=64)
    prev_hash = models.CharField(max_length=64, blank=True)
    seal_hash = models.CharField(max_length=64, verbose_name="Siegel-Prüfsumme")
    signature = models.TextField()
    public_key = models.CharField(max_length=64)
    key_id = models.CharField(max_length=16)
    created_at = models.DateTimeField()

    class Meta:
        verbose_name = "Siegel"
        verbose_name_plural = "Siegel"
        ordering = ["created_at", "pk"]
        indexes = [models.Index(fields=["subject_type", "subject_id"])]

    def __str__(self):
        return f"{self.get_kind_display()} {self.public_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Siegel sind unveränderlich.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Siegel sind unveränderlich.")
