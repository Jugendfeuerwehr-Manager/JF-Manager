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
        permissions = [("invite_portal_account", "Portalzugänge einladen und verwalten")]
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


class ParentAccessExtension(models.Model):
    """Staff-granted parent access beyond the child's 18th birthday (E6, at most 12 months)."""

    parent = models.ForeignKey("members.Parent", on_delete=models.CASCADE, related_name="access_extensions")
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="parent_access_extensions")
    until = models.DateField(verbose_name="Elternzugriff bis")
    reason = models.CharField(max_length=500, verbose_name="Begründung")
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Verlängerung Elternzugriff"
        verbose_name_plural = "Verlängerungen Elternzugriff"
        ordering = ["-until"]

    def __str__(self):
        return f"{self.parent} → {self.member} bis {self.until:%d.%m.%Y}"


class PortalPolicy(models.Model):
    """What parents and members see, and who gets a member account (PORTAL-02, E7, D3).

    ``department`` NULL is the organisation row: defaults plus ceiling. Department
    rows only hold their deviations; an empty value inherits the organisation.
    """

    MEMBER_PORTAL_MODES = [
        ("", "Wie Organisation"),
        ("off", "Keine Mitgliederkonten"),
        ("min_age", "Ab Alter"),
        ("all", "Alle"),
    ]

    department = models.OneToOneField(
        "departments.Department", null=True, blank=True, on_delete=models.CASCADE, related_name="portal_policy"
    )
    member_portal_mode = models.CharField(max_length=10, choices=MEMBER_PORTAL_MODES, blank=True, default="")
    member_portal_min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    visibility = models.JSONField(default=dict, blank=True)
    ceiling = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Portal-Freigabe"
        verbose_name_plural = "Portal-Freigaben"
        constraints = [
            models.UniqueConstraint(
                fields=["department"], condition=models.Q(department__isnull=True), name="one_org_portal_policy"
            ),
        ]

    def __str__(self):
        return f"Portal-Freigabe {self.department or 'Organisation'}"


class ChangeRequest(models.Model):
    """Requested change of name and contact data (PORTAL-03, E2: nothing changes before approval).

    ``fields`` holds one entry per requested field: ``{"field", "old", "new", "decision", "current_at_decision"}``;
    ``old`` is the value when the request was made, so reviewers see conflicts with later changes.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        PARTIAL = "partial", "Teilweise übernommen"
        APPLIED = "applied", "Übernommen"
        REJECTED = "rejected", "Abgelehnt"
        WITHDRAWN = "withdrawn", "Zurückgezogen"

    target_member = models.ForeignKey(
        "members.Member", null=True, blank=True, on_delete=models.CASCADE, related_name="change_requests"
    )
    target_parent = models.ForeignKey(
        "members.Parent", null=True, blank=True, on_delete=models.CASCADE, related_name="change_requests"
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    version = models.PositiveIntegerField(default=1)
    fields = models.JSONField(default=list)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=1000, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Änderungsantrag"
        verbose_name_plural = "Änderungsanträge"
        ordering = ["-updated_at"]
        permissions = [("review_changerequest", "Änderungsanträge aus dem Portal prüfen")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(target_member__isnull=False, target_parent__isnull=True)
                | models.Q(target_member__isnull=True, target_parent__isnull=False),
                name="change_request_has_one_target",
            ),
            models.UniqueConstraint(
                fields=["target_member"],
                condition=models.Q(status="open", target_member__isnull=False),
                name="one_open_change_request_per_member",
            ),
            models.UniqueConstraint(
                fields=["target_parent"],
                condition=models.Q(status="open", target_parent__isnull=False),
                name="one_open_change_request_per_parent",
            ),
        ]

    @property
    def target(self):
        return self.target_member if self.target_member_id else self.target_parent

    @property
    def kind(self):
        return "member" if self.target_member_id else "parent"


class ChangeLog(models.Model):
    """Append-only record of applied values (who, when, field, old, new, request)."""

    target_kind = models.CharField(max_length=10)  # member | parent
    target_id = models.PositiveBigIntegerField()
    field = models.CharField(max_length=30)
    old = models.CharField(max_length=300, blank=True, default="")
    new = models.CharField(max_length=300, blank=True, default="")
    change_request = models.ForeignKey(
        ChangeRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="log"
    )
    applied_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    applied_at = models.DateTimeField(auto_now_add=True)
    self_change = models.BooleanField(default=False)  # PORTAL-04 (E14)

    class Meta:
        verbose_name = "Änderungsprotokoll"
        verbose_name_plural = "Änderungsprotokoll"
        ordering = ["-applied_at"]
        indexes = [models.Index(fields=["target_kind", "target_id"])]
