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


class Invitation(models.Model):
    """Invitation of a parent or member record to the portal (E1: invitation only).

    Only a SHA-256 hash of the one-time token is stored. At most one open
    invitation per record; resending renews token and expiry.
    """

    VALIDITY_DAYS = 7

    parent = models.ForeignKey(
        "members.Parent", null=True, blank=True, on_delete=models.CASCADE, related_name="portal_invitations"
    )
    member = models.ForeignKey(
        "members.Member", null=True, blank=True, on_delete=models.CASCADE, related_name="portal_invitations"
    )
    email = models.EmailField(verbose_name="E-Mail")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Portaleinladung"
        verbose_name_plural = "Portaleinladungen"
        ordering = ["-created_at"]
        permissions = [("invite_portal_account", "Eltern und Mitglieder ins Portal einladen")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(parent__isnull=False, member__isnull=True)
                | models.Q(parent__isnull=True, member__isnull=False),
                name="invitation_has_one_target",
            ),
            models.UniqueConstraint(
                fields=["parent"],
                condition=models.Q(accepted_at__isnull=True, revoked_at__isnull=True, parent__isnull=False),
                name="one_open_invitation_per_parent",
            ),
            models.UniqueConstraint(
                fields=["member"],
                condition=models.Q(accepted_at__isnull=True, revoked_at__isnull=True, member__isnull=False),
                name="one_open_invitation_per_member",
            ),
        ]

    def __str__(self):
        return f"Einladung {self.email} ({self.state})"

    @property
    def kind(self):
        return "parent" if self.parent_id else "member"

    @property
    def record(self):
        return self.parent if self.parent_id else self.member

    @property
    def state(self):
        from django.utils import timezone

        if self.accepted_at:
            return "accepted"
        if self.revoked_at:
            return "revoked"
        if self.expires_at <= timezone.now():
            return "expired"
        return "open"
