"""Participation in planned services (PART-01.1, concept 4.5 and 5.1).

Positions (``Slot``), minimum staffing and the waiting list per position belong to PART-04
(concept 4.7).
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Value


class Mode(models.TextChoices):
    OPT_OUT = "opt_out", "Abmeldung"
    OPT_IN = "opt_in", "Anmeldung"
    ASSIGNMENT = "assignment", "Zuteilung"


class WaitlistMode(models.TextChoices):
    AUTO = "auto", "Automatisch nachrücken"
    MANUAL = "manual", "Manuell"


class ParticipationDefaults(models.Model):
    """Defaults per department; ``department`` NULL is the organisation row (E3, E4, E5)."""

    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="participation_defaults",
        verbose_name="Abteilung",
    )
    mode = models.CharField(max_length=12, choices=Mode.choices, default=Mode.OPT_OUT, verbose_name="Teilnahmemodus")
    registration_offset_h = models.PositiveIntegerField(
        default=48, validators=[MaxValueValidator(24 * 90)], verbose_name="Anmeldeschluss (Stunden vor Beginn)"
    )
    cancellation_offset_h = models.PositiveIntegerField(
        default=2, validators=[MaxValueValidator(24 * 90)], verbose_name="Abmeldeschluss (Stunden vor Beginn)"
    )
    waitlist_mode = models.CharField(
        max_length=8, choices=WaitlistMode.choices, default=WaitlistMode.AUTO, verbose_name="Warteliste"
    )
    urgent_notice_h = models.PositiveIntegerField(
        default=24,
        validators=[MinValueValidator(0), MaxValueValidator(24 * 90)],
        verbose_name="Sofortmeldung bei Änderung (Stunden vor Beginn)",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Teilnahme-Standard"
        verbose_name_plural = "Teilnahme-Standards"
        constraints = [
            models.UniqueConstraint(
                fields=["department"], condition=Q(department__isnull=False), name="participation_defaults_dept_unique"
            ),
            # One organisation row: every row with a NULL department collides on the constant.
            models.UniqueConstraint(
                Value(1), condition=Q(department__isnull=True), name="participation_defaults_org_unique"
            ),
        ]

    def __str__(self):
        return f"Standard {self.department or 'Organisation'}"


class SessionParticipation(models.Model):
    session = models.OneToOneField(
        "training.TrainingSession", on_delete=models.CASCADE, related_name="participation", verbose_name="Dienst"
    )
    mode = models.CharField(max_length=12, choices=Mode.choices, default=Mode.OPT_OUT, verbose_name="Teilnahmemodus")
    portal_visible = models.BooleanField(default=True, verbose_name="Im Portal sichtbar")
    public_note = models.CharField(max_length=1000, blank=True, default="", verbose_name="Hinweis für Teilnehmende")
    registration_opens_at = models.DateTimeField(null=True, blank=True)
    registration_closes_at = models.DateTimeField(null=True, blank=True)
    cancellation_closes_at = models.DateTimeField(null=True, blank=True)
    # With positions this is derived: sum of the position maxima plus ``extra_places`` (concept 4.7).
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    min_participants = models.PositiveIntegerField(null=True, blank=True)
    # "Weitere Teilnehmende ohne Position" (e.g. guests); only meaningful with positions.
    extra_places = models.PositiveIntegerField(null=True, blank=True, verbose_name="Weitere Plätze ohne Position")
    waitlist_mode = models.CharField(max_length=8, choices=WaitlistMode.choices, default=WaitlistMode.AUTO)
    # Rule language v1 (participation.rules); {} means no requirement.
    eligibility = models.JSONField(default=dict, blank=True)
    revision = models.PositiveBigIntegerField(default=1)
    # Assignment mode (PART-04.4): draft {"entries": {member_id: slot_id | "extra"}} until published.
    assignment_draft = models.JSONField(default=dict, blank=True)
    assignment_published_at = models.DateTimeField(null=True, blank=True)
    # "Bewerbungen offen lassen": unassigned applicants stay applied instead of not selected.
    assignment_keep_open = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Teilnahme-Konfiguration"
        verbose_name_plural = "Teilnahme-Konfigurationen"

    def __str__(self):
        return f"Teilnahme {self.session_id}"


class Slot(models.Model):
    """A named position of a service with minimum (staffing) and maximum (places) and its own rule."""

    participation = models.ForeignKey(
        SessionParticipation, on_delete=models.CASCADE, related_name="slots", verbose_name="Teilnahme"
    )
    label = models.CharField(max_length=80, verbose_name="Bezeichnung")
    min_count = models.PositiveSmallIntegerField(default=0, verbose_name="Mindestens")
    max_count = models.PositiveSmallIntegerField(default=1, verbose_name="Plätze")
    # Rule language v1 (participation.rules), in addition to the general requirements; {} = none.
    rule = models.JSONField(default=dict, blank=True)
    position = models.PositiveSmallIntegerField(default=0, verbose_name="Reihenfolge")

    class Meta:
        verbose_name = "Position"
        verbose_name_plural = "Positionen"
        ordering = ["position", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(min_count__lte=models.F("max_count")), name="slot_min_lte_max"),
            models.CheckConstraint(condition=Q(max_count__gte=1), name="slot_max_positive"),
        ]

    def __str__(self):
        return self.label


class Registration(models.Model):
    class State(models.TextChoices):
        # In opt-out services "registered" is the confirmed/expected state: it is what a taken-back
        # cancellation returns to; a person without a row is "expected" as well (no row is ever deleted).
        REGISTERED = "registered", "Angemeldet"
        WAITLISTED = "waitlisted", "Warteliste"
        APPLIED = "applied", "Beworben"
        ASSIGNED = "assigned", "Zugeteilt"
        NOT_SELECTED = "not_selected", "Nicht berücksichtigt"
        CANCELLED = "cancelled", "Abgemeldet"

    class Reason(models.TextChoices):
        ILLNESS = "krankheit", "Krankheit"
        SCHOOL_WORK = "schule_beruf", "Schule/Beruf"
        HOLIDAY = "urlaub", "Urlaub"
        FAMILY = "familie", "Familie"
        OTHER = "sonstiges", "Sonstiges"

    class Source(models.TextChoices):
        PORTAL_PARENT = "portal_parent", "Elternkonto"
        PORTAL_MEMBER = "portal_member", "Mitgliedskonto"
        STAFF = "staff", "Betreuende"

    session = models.ForeignKey("training.TrainingSession", on_delete=models.CASCADE, related_name="registrations")
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="registrations")
    state = models.CharField(max_length=12, choices=State.choices)
    # Position held while registered/assigned (NULL: no positions or a place without position).
    slot = models.ForeignKey(Slot, null=True, blank=True, on_delete=models.SET_NULL, related_name="registrations")
    # Position asked for (Anmeldung) or wished (Zuteilung, Q3); NULL = any suitable position.
    preferred_slot = models.ForeignKey(Slot, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reason_category = models.CharField(max_length=12, choices=Reason.choices, blank=True, default="")
    # Short free text, visible to responsible staff only, deleted 90 days after the service (D4).
    reason_note = models.CharField(max_length=200, blank=True, default="")
    source = models.CharField(max_length=14, choices=Source.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    state_changed_at = models.DateTimeField()
    conflict = models.BooleanField(default=False)
    conflict_reasons = models.JSONField(default=list, blank=True)
    late = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Meldung"
        verbose_name_plural = "Meldungen"
        constraints = [models.UniqueConstraint(fields=["session", "member"], name="registration_unique_member")]
        indexes = [models.Index(fields=["session", "state", "created_at"], name="registration_session_state")]

    def __str__(self):
        return f"{self.member_id} @ {self.session_id}: {self.state}"


class RegistrationEvent(models.Model):
    """Append-only history of state changes."""

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    from_state = models.CharField(max_length=12, blank=True, default="")
    to_state = models.CharField(max_length=12)
    at = models.DateTimeField()
    via = models.CharField(max_length=14)  # a Registration.Source value or "system" (waitlist promotion)

    class Meta:
        ordering = ["at", "pk"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("RegistrationEvent is append-only.")
        super().save(*args, **kwargs)
