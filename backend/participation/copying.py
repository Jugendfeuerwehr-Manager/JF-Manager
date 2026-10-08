"""Carry the participation configuration of a service into an independent copy (PART-01.5, concept 4.5).

Registrations are never copied. An absolute deadline is only present when staff set it explicitly;
it is shifted by the date difference (same local wall time) and never later than the start of the
target. Deadlines left empty keep following the start of each occurrence through the defaults.
"""

from datetime import datetime, timedelta

from django.utils import timezone

from .models import SessionParticipation

COPIED_FIELDS = (
    "mode",
    "portal_visible",
    "public_note",
    "max_participants",
    "min_participants",
    "waitlist_mode",
)
DEADLINE_FIELDS = ("registration_opens_at", "registration_closes_at", "cancellation_closes_at")


def shift_deadline(value, days, target_start):
    """Same local wall time ``days`` later, capped at ``target_start``."""
    if value is None:
        return None
    local = timezone.localtime(value)
    shifted = timezone.make_aware(datetime.combine(local.date() + timedelta(days=days), local.time()))
    return min(shifted, target_start)


def copy_configuration(source, target):
    """Copy the configuration row of ``source`` to ``target`` (both ``TrainingSession``).

    Without an explicit row on ``source`` nothing is written: the defaults apply to the copy too.
    Returns the new ``SessionParticipation`` or ``None``.
    """
    row = SessionParticipation.objects.filter(session=source).first()
    if row is None:
        return None
    days = (target.date - source.date).days
    start = timezone.make_aware(datetime.combine(target.date, target.start_time))
    values = {name: getattr(row, name) for name in COPIED_FIELDS}
    values.update({name: shift_deadline(getattr(row, name), days, start) for name in DEADLINE_FIELDS})
    return SessionParticipation.objects.update_or_create(
        session=target, defaults={**values, "eligibility": row.eligibility}
    )[0]
