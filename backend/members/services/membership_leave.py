"""Leaving the organisation. The leave date starts the anonymization deadline (DSGVO)."""

from datetime import timedelta

from rest_framework.exceptions import ValidationError


def record_leave(member, *, left_at, status=None):
    """Set (or with ``left_at=None`` withdraw) the leave date, optionally with a new status."""
    if left_at is not None and member.joined and left_at < member.joined:
        raise ValidationError({"left_at": "Der Austritt kann nicht vor dem Eintritt liegen."})
    member.left_at = left_at
    fields = ["left_at"]
    if status is not None:
        member.status = status
        fields.append("status")
    member.save(update_fields=fields)
    return member


def anonymize_due(member):
    """Date on which the automatic anonymization takes place, or ``None``."""
    if member.left_at is None or member.anonymized_at is not None:
        return None
    from privacy.services.retention import retention_days

    return member.left_at + timedelta(days=retention_days("member_anonymize_after_days"))
