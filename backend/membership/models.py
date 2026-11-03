from django.conf import settings
from django.db import models


class MembershipEvent(models.Model):
    """One movement in a member's membership, per department. Reports count these."""

    class Kind(models.TextChoices):
        JOINED_NEW = "joined_new", "Zugang neu"
        JOINED_OTHER_ORG = "joined_other_org", "Zugang aus anderer Organisation"
        JOINED_FROM_KF = "joined_from_kf", "Zugang aus Kinderfeuerwehr"
        STAGE_CHANGED = "stage_changed", "Stufe geändert"
        EXIT_EA = "exit_ea", "Abgang in die Einsatzabteilung"
        EXIT_OTHER = "exit_other", "Abgang sonstige"

    class ExitReason(models.TextChoices):
        RELOCATION = "relocation", "Wohnortwechsel"
        LOST_INTEREST = "lost_interest", "Interesse an JF verloren"
        SCHOOL = "school", "Belastung durch Schule"
        VOCATIONAL_TRAINING = "vocational_training", "Berufsausbildung"
        EXPELLED = "expelled", "Verweis bzw. Ausschluss aus der JF"
        NO_TRANSFER_EA = "no_transfer_ea", "Möchte keine Übernahme in EA"

    JOIN_KINDS = (Kind.JOINED_NEW, Kind.JOINED_OTHER_ORG, Kind.JOINED_FROM_KF)
    EXIT_KINDS = (Kind.EXIT_EA, Kind.EXIT_OTHER)

    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="membership_events", verbose_name="Mitglied"
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="membership_events",
        verbose_name="Abteilung",
    )
    date = models.DateField(verbose_name="Datum")
    kind = models.CharField(max_length=20, choices=Kind.choices, verbose_name="Art")
    exit_reason = models.CharField(max_length=30, choices=ExitReason.choices, blank=True, verbose_name="Austrittsgrund")
    from_status = models.ForeignKey(
        "members.Status", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Von"
    )
    to_status = models.ForeignKey(
        "members.Status", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Nach"
    )
    note = models.CharField(max_length=300, blank=True, verbose_name="Notiz")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mitgliedschaftsereignis"
        verbose_name_plural = "Mitgliedschaftsereignisse"
        ordering = ["-date", "-pk"]
        indexes = [models.Index(fields=["department", "kind", "date"])]

    def __str__(self):
        return f"{self.get_kind_display()} {self.date:%d.%m.%Y}"
