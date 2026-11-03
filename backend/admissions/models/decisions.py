from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CommitteeMeeting(models.Model):
    """A meeting of the body that decides on admissions (e.g. the youth committee)."""

    department = models.ForeignKey(
        "departments.Department", on_delete=models.CASCADE, related_name="committee_meetings"
    )
    body = models.CharField(max_length=100, verbose_name="Gremium")
    date = models.DateField(verbose_name="Sitzungsdatum")
    protocol_ref = models.CharField(max_length=200, blank=True, verbose_name="Protokoll")
    note = models.TextField(blank=True, verbose_name="Notiz")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "Sitzung"
        verbose_name_plural = "Sitzungen"
        ordering = ["-date", "-pk"]

    def __str__(self):
        return f"{self.body} {self.date:%d.%m.%Y}"


class AdmissionDecision(models.Model):
    """The recorded resolution on one application. Sealed on creation, never changed."""

    class Outcome(models.TextChoices):
        APPROVED = "approved", "Angenommen"
        REJECTED = "rejected", "Abgelehnt"
        DEFERRED = "deferred", "Zurückgestellt"

    application = models.ForeignKey("admissions.Application", on_delete=models.CASCADE, related_name="decisions")
    meeting = models.ForeignKey(
        CommitteeMeeting, on_delete=models.PROTECT, null=True, blank=True, related_name="decisions"
    )
    body = models.CharField(max_length=100, verbose_name="Gremium")
    decided_on = models.DateField(verbose_name="Beschlossen am")
    outcome = models.CharField(max_length=10, choices=Outcome.choices, verbose_name="Ergebnis")
    votes_yes = models.PositiveSmallIntegerField(null=True, blank=True)
    votes_no = models.PositiveSmallIntegerField(null=True, blank=True)
    votes_abstain = models.PositiveSmallIntegerField(null=True, blank=True)
    note = models.TextField(blank=True, verbose_name="Begründung / Notiz")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aufnahmebeschluss"
        verbose_name_plural = "Aufnahmebeschlüsse"
        ordering = ["recorded_at", "pk"]

    def __str__(self):
        return f"{self.get_outcome_display()} am {self.decided_on:%d.%m.%Y}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Beschlüsse sind versiegelt; bitte einen neuen Beschluss erfassen.")
        super().save(*args, **kwargs)
