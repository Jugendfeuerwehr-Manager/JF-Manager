from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone


class MemberList(models.Model):
    """
    A named list of members. Members can belong to multiple lists (unlike Group).
    Designed for checklists, event participation, excursions, etc.
    """

    name = models.CharField(max_length=200, verbose_name="Listenname")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="member_lists",
        verbose_name="Abteilung",
        help_text="Ohne Abteilung nur für organisationsweite Listen oder ungeklärte Altlisten.",
    )
    organization_wide = models.BooleanField(
        default=False,
        verbose_name="Organisationsweit",
        help_text="Liste einer Organisation ohne Abteilungen; nur mit organisationsweitem Recht sichtbar.",
    )
    description = models.TextField(blank=True, default="", verbose_name="Beschreibung")
    color = models.CharField(max_length=7, default="#3B82F6", verbose_name="Farbe")
    attachments = GenericRelation("Attachment", related_query_name="memberlist")
    legacy_resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Altlistenklärung abgeschlossen")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mitgliederliste"
        verbose_name_plural = "Mitgliederlisten"
        ordering = ["name"]
        permissions = [("export_memberlist", "Kann Mitgliederlisten exportieren")]
        constraints = [
            models.CheckConstraint(
                check=models.Q(organization_wide=False) | models.Q(department__isnull=True),
                name="organization_wide_list_without_department",
            )
        ]

    def __str__(self):
        return self.name

    @property
    def is_unresolved_legacy(self):
        return self.department_id is None and not self.organization_wide

    @property
    def member_count(self):
        return self.entries.count()

    @property
    def checked_count(self):
        return self.entries.filter(checked=True).count()


class MemberListEntry(models.Model):
    """
    Through-table connecting a Member to a MemberList with optional check state and notes.
    """

    member_list = models.ForeignKey(
        MemberList,
        on_delete=models.CASCADE,
        related_name="entries",
        verbose_name="Liste",
    )
    member = models.ForeignKey(
        "Member",
        on_delete=models.CASCADE,
        related_name="list_entries",
        verbose_name="Mitglied",
    )
    checked = models.BooleanField(default=False, verbose_name="Abgehakt")
    checked_at = models.DateTimeField(null=True, blank=True, verbose_name="Abgehakt am")
    notes = models.CharField(max_length=500, blank=True, default="", verbose_name="Notiz")
    added_at = models.DateTimeField(auto_now_add=True)
    # Raised on every change of check state or note; clients send the version
    # they saw, so a stale write is answered with the current state (UX-03.2).
    version = models.PositiveIntegerField(default=1, verbose_name="Version")

    class Meta:
        verbose_name = "Listeneintrag"
        verbose_name_plural = "Listeneinträge"
        unique_together = [("member_list", "member")]
        ordering = ["member__lastname", "member__name"]

    def __str__(self):
        return f"{self.member_list.name} – {self.member}"

    def toggle_check(self):
        self.checked = not self.checked
        self.checked_at = timezone.now() if self.checked else None
        self.version += 1
        self.save(update_fields=["checked", "checked_at", "version"])


class MemberListLegacyTarget(models.Model):
    """Stable destination for an explicitly resolved legacy source and department."""

    source = models.ForeignKey(MemberList, on_delete=models.PROTECT, related_name="legacy_targets")
    department = models.ForeignKey("departments.Department", on_delete=models.PROTECT)
    target = models.OneToOneField(MemberList, on_delete=models.PROTECT, related_name="legacy_source_mapping")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "department"], name="unique_legacy_list_target")]
