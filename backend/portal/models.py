from django.conf import settings
from django.db import models


class AccountLink(models.Model):
    """Binds one account to at most one parent record and one member record.

    Portal accounts (parents, members) and staff accounts that are members
    themselves (PORTAL-04) use the same link. It only takes effect once
    confirmed: an invitation confirms on acceptance, a staff link when the
    account confirms it after login.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Ausstehend"
        CONFIRMED = "confirmed", "Bestätigt"
        REJECTED = "rejected", "Abgelehnt"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_link",
        verbose_name="Konto",
    )
    parent = models.OneToOneField(
        "members.Parent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="account_link",
        verbose_name="Elterndatensatz",
    )
    member = models.OneToOneField(
        "members.Member",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="account_link",
        verbose_name="Mitgliedsdatensatz",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, verbose_name="Status")
    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Verknüpft von",
    )
    linked_at = models.DateTimeField(auto_now_add=True, verbose_name="Verknüpft am")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="Bestätigt am")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="Abgelehnt am")

    class Meta:
        verbose_name = "Kontoverknüpfung"
        verbose_name_plural = "Kontoverknüpfungen"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(parent__isnull=False) | models.Q(member__isnull=False),
                name="account_link_has_target",
            ),
        ]

    def __str__(self):
        return f"{self.user} ({self.get_status_display()})"

    @property
    def is_effective(self):
        return self.status == self.Status.CONFIRMED
