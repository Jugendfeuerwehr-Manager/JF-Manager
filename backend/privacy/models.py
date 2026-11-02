"""Legal texts (imprint, privacy notice) and consent records (DSGVO)."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class LegalPage(models.Model):
    """One editable legal text per kind; the draft is what the editor works on."""

    class Kind(models.TextChoices):
        IMPRINT = "imprint", "Impressum"
        PRIVACY = "privacy", "Datenschutzerklärung"

    kind = models.CharField(max_length=20, choices=Kind.choices, unique=True, verbose_name="Art")
    draft_title = models.CharField(max_length=200, blank=True, verbose_name="Titel (Entwurf)")
    draft_body = models.TextField(blank=True, verbose_name="Text (Entwurf)")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Zuletzt geändert")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "Rechtstext"
        verbose_name_plural = "Rechtstexte"

    def __str__(self):
        return self.get_kind_display()

    @property
    def current_version(self):
        return self.versions.order_by("-version").first()


class LegalPageVersion(models.Model):
    """A published, immutable state of a legal text; consents refer to it by number."""

    page = models.ForeignKey(LegalPage, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField(verbose_name="Version")
    title = models.CharField(max_length=200, verbose_name="Titel")
    body = models.TextField(verbose_name="Text")
    change_note = models.CharField(max_length=300, blank=True, verbose_name="Änderungshinweis")
    published_at = models.DateTimeField(default=timezone.now, verbose_name="Veröffentlicht am")
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "Rechtstext-Version"
        verbose_name_plural = "Rechtstext-Versionen"
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["page", "version"], name="privacy_unique_page_version")]

    def __str__(self):
        return f"{self.page} v{self.version}"


class ConsentKind(models.Model):
    """A kind of consent. Built-in kinds are seeded; admins add their own.

    ``description`` is the wording people agree to; changing it raises
    ``version`` so every record keeps the version it was given for.
    """

    slug = models.SlugField(max_length=50, unique=True, verbose_name="Kennung")
    label = models.CharField(max_length=200, verbose_name="Bezeichnung")
    description = models.TextField(blank=True, verbose_name="Wortlaut")
    version = models.PositiveIntegerField(default=1, editable=False, verbose_name="Version")
    in_portal = models.BooleanField(
        default=False, verbose_name="Im Portal", help_text="Eltern erteilen und widerrufen sie im Portal je Kind."
    )
    active = models.BooleanField(default=True, verbose_name="Aktiv")
    built_in = models.BooleanField(default=False, editable=False, verbose_name="Mitgeliefert")
    position = models.PositiveIntegerField(default=0, verbose_name="Reihenfolge")

    class Meta:
        ordering = ["position", "label"]
        verbose_name = "Einwilligungsart"
        verbose_name_plural = "Einwilligungsarten"

    def __str__(self):
        return self.label

    @property
    def text_version(self):
        return f"{self.slug}:v{self.version}"


class ConsentRecord(models.Model):
    """Append-only evidence of a consent or acknowledgement (Art. 7 Abs. 1 DSGVO).

    Withdrawing adds a new row; the newest row per subject and kind is the
    current state. Exactly one of user, member and parent is the subject.
    """

    class Status(models.TextChoices):
        GRANTED = "granted", "Erteilt"
        WITHDRAWN = "withdrawn", "Widerrufen"

    class Source(models.TextChoices):
        SELF = "self", "Selbst erklärt"
        STAFF = "staff", "Von der Leitung erfasst"
        APPLICATION = "application", "Mitgliedsantrag"
        IMPORT = "import", "Übernommen"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="consent_records"
    )
    member = models.ForeignKey(
        "members.Member", null=True, blank=True, on_delete=models.CASCADE, related_name="consent_records"
    )
    parent = models.ForeignKey(
        "members.Parent", null=True, blank=True, on_delete=models.CASCADE, related_name="consent_records"
    )
    kind = models.SlugField(max_length=50, verbose_name="Art")
    status = models.CharField(max_length=10, choices=Status.choices, verbose_name="Status")
    text_version = models.CharField(max_length=50, blank=True, verbose_name="Textversion")
    text_snapshot = models.TextField(blank=True, verbose_name="Wortlaut")
    source = models.CharField(max_length=20, choices=Source.choices, verbose_name="Herkunft")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    recorded_at = models.DateTimeField(default=timezone.now, verbose_name="Erfasst am")
    note = models.CharField(max_length=300, blank=True, verbose_name="Notiz")

    class Meta:
        verbose_name = "Einwilligung"
        verbose_name_plural = "Einwilligungen"
        ordering = ["-recorded_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(user__isnull=False, member__isnull=True, parent__isnull=True)
                    | Q(user__isnull=True, member__isnull=False, parent__isnull=True)
                    | Q(user__isnull=True, member__isnull=True, parent__isnull=False)
                ),
                name="privacy_consent_exactly_one_subject",
            )
        ]
        indexes = [
            models.Index(fields=["member", "kind"]),
            models.Index(fields=["parent", "kind"]),
            models.Index(fields=["user", "kind"]),
        ]

    def __str__(self):
        return f"{self.kind}: {self.get_status_display()}"
