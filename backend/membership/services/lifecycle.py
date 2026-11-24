"""Membership movements. Every join, stage change and exit goes through here so reports can count it.

Events are written per department: a member in two departments counts in both reports.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from members.services.membership_leave import record_leave
from membership.models import MembershipEvent

Kind = MembershipEvent.Kind


def _department_ids(member):
    return list(member.departments.values_list("id", flat=True)) or [None]


def _write(member, *, kind, on, by=None, department_ids=None, **fields):
    department_ids = department_ids if department_ids is not None else _department_ids(member)
    return MembershipEvent.objects.bulk_create(
        MembershipEvent(member=member, department_id=department_id, date=on, kind=kind, created_by=by, **fields)
        for department_id in department_ids
    )


def admit(member, *, on=None, kind=Kind.JOINED_NEW, by=None, note=""):
    """Record that ``member`` joined (call after the departments are assigned)."""
    if kind not in MembershipEvent.JOIN_KINDS:
        raise ValidationError({"kind": "Keine gültige Zugangsart."})
    on = on or member.joined or timezone.localdate()
    return _write(member, kind=kind, on=on, by=by, to_status=member.status, note=note)


def record_stage_change(member, *, from_status, by=None, on=None):
    """Log a status change that was saved on ``member``; does nothing if the status stayed."""
    if (from_status.pk if from_status else None) == member.status_id:
        return []
    return _write(
        member,
        kind=Kind.STAGE_CHANGED,
        on=on or timezone.localdate(),
        by=by,
        from_status=from_status,
        to_status=member.status,
    )


def record_department_changes(member, *, added, removed, by=None, on=None):
    """Moving between departments is a transfer: a join in the new one, an exit in the old one.

    The exit has no reason yet; the annual report lists it so the leadership can complete it.
    """
    on = on or timezone.localdate()
    events = []
    if added:
        events += _write(member, kind=Kind.JOINED_OTHER_ORG, on=on, by=by, department_ids=list(added))
    if removed:
        events += _write(member, kind=Kind.EXIT_OTHER, on=on, by=by, department_ids=list(removed))
    return events


def record_exit(member, *, left_at, status=None, kind=Kind.EXIT_OTHER, exit_reason="", by=None, note=""):
    """Leave (or with ``left_at=None`` withdraw the leave) and log the movement.

    Wraps ``members.services.membership_leave.record_leave``, the only writer of ``left_at``.
    """
    if left_at is not None and kind not in MembershipEvent.EXIT_KINDS:
        raise ValidationError({"kind": "Keine gültige Abgangsart."})
    if exit_reason and kind != Kind.EXIT_OTHER:
        raise ValidationError({"exit_reason": "Ein Grund gehört nur zu „Abgang sonstige“."})

    with transaction.atomic():
        previous_left_at = member.left_at
        previous_status = member.status
        record_leave(member, left_at=left_at, status=status)
        # A withdrawn or re-dated leave replaces the movement logged for the old date.
        if previous_left_at is not None:
            member.membership_events.filter(kind__in=MembershipEvent.EXIT_KINDS, date=previous_left_at).delete()
        if left_at is None:
            return member
        _write(
            member,
            kind=kind,
            on=left_at,
            by=by,
            exit_reason=exit_reason,
            from_status=previous_status,
            to_status=member.status,
            note=note,
        )
    return member
