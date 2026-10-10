"""Versioned writes on member list entries (UX-03.2).

Every change of check state or note raises ``MemberListEntry.version``. A
client sends the version it last saw; if someone else changed the entry in
the meantime the write is refused with the current state instead of silently
overwriting it. Rows are locked for the read-compare-write, so two parallel
requests with the same expected version cannot both win on PostgreSQL.
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from members.models import MemberListEntry


class EntryNotFound(Exception):
    pass


class EntryVersionConflict(Exception):
    def __init__(self, entry):
        super().__init__("Der Eintrag wurde inzwischen geändert.")
        self.entry = entry


def entry_state(entry):
    """Current state of one entry as the client needs it to resolve a conflict."""
    return {
        "id": entry.pk,
        "member_id": entry.member_id,
        "checked": entry.checked,
        "checked_at": entry.checked_at,
        "notes": entry.notes,
        "version": entry.version,
    }


def _locked_entry(member_list, member_id):
    try:
        return MemberListEntry.objects.select_for_update().get(member_list=member_list, member_id=member_id)
    except (MemberListEntry.DoesNotExist, ValueError, TypeError) as exc:
        raise EntryNotFound from exc


def set_entry_check(member_list, member_id, checked=None, expected_version=None):
    """Set (or with ``checked=None`` toggle) one entry; returns the saved entry.

    Reaching the requested state is not a conflict: when two people tick the
    same person, both succeed and the version rises once.
    """
    with transaction.atomic():
        entry = _locked_entry(member_list, member_id)
        target = (not entry.checked) if checked is None else bool(checked)
        if entry.checked == target and checked is not None:
            return entry
        if expected_version is not None and entry.version != expected_version:
            raise EntryVersionConflict(entry)
        entry.checked = target
        entry.checked_at = timezone.now() if target else None
        entry.version += 1
        entry.save(update_fields=["checked", "checked_at", "version"])
        return entry


def set_entry_notes(member_list, member_id, notes, expected_version=None):
    with transaction.atomic():
        entry = _locked_entry(member_list, member_id)
        if entry.notes == notes:
            return entry
        if expected_version is not None and entry.version != expected_version:
            raise EntryVersionConflict(entry)
        entry.notes = notes
        entry.version += 1
        entry.save(update_fields=["notes", "version"])
        return entry


def bulk_check_candidates(member_list, checked, member_ids=None):
    """Entries a bulk check/uncheck would change, for preview and execution."""
    entries = member_list.entries.exclude(checked=checked)
    if member_ids is not None:
        entries = entries.filter(member_id__in=member_ids)
    return entries


def bulk_set_check(member_list, checked, member_ids):
    """Apply a previewed bulk change to exactly the previewed, still differing entries.

    Entries changed by someone else since the preview already have the target
    state and are therefore skipped instead of being touched again.
    """
    with transaction.atomic():
        ids = list(
            bulk_check_candidates(member_list, checked, member_ids)
            .order_by("pk")
            .select_for_update()
            .values_list("pk", flat=True)
        )
        changed = MemberListEntry.objects.filter(pk__in=ids).update(
            checked=checked,
            checked_at=timezone.now() if checked else None,
            version=F("version") + 1,
        )
    return changed
