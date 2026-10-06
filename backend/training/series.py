"""Bounded, versioned series previews that never erase existing exercises."""

import calendar
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from training.api.permissions import can_manage_training_department
from training.api.validation import validate_block_times, validate_session_times
from training.copying import copied_files, copy_session, snapshot_hash
from training.models import TrainingSession

MAX_OCCURRENCES = 200
MAX_MONTHS = 24
FREQUENCIES = ("WEEKLY", "BIWEEKLY", "MONTHLY")


class SeriesInputSerializer(serializers.Serializer):
    window_start = serializers.DateField(required=False)
    window_end = serializers.DateField(required=False)
    preview_token = serializers.CharField(required=False, max_length=64)


def add_months(anchor, count):
    """Always derive from the original day: 31.01. -> 28./29.02. -> 31.03."""
    index = anchor.year * 12 + anchor.month - 1 + count
    year, month_index = divmod(index, 12)
    month = month_index + 1
    return date(year, month, min(anchor.day, calendar.monthrange(year, month)[1]))


def occurrence_date(anchor, frequency, index):
    if frequency == "MONTHLY":
        return add_months(anchor, index)
    return anchor + timedelta(days=index * (7 if frequency == "WEEKLY" else 14))


def validate_recurrence_rule(rule, session_date):
    """Shared by the session serializer and every series action."""
    if rule is None:
        return None
    if not isinstance(rule, dict) or set(rule) - {"frequency", "end_date"}:
        raise serializers.ValidationError({"recurrence_rule": "Ungültige Wiederholungsregel."})
    if rule.get("frequency") not in FREQUENCIES:
        raise serializers.ValidationError({"recurrence_rule": "Unbekannte Wiederholungsfrequenz."})
    try:
        end = date.fromisoformat(rule.get("end_date") or "")
    except (ValueError, TypeError) as exc:
        raise serializers.ValidationError({"recurrence_rule": "Gültiges Enddatum erforderlich."}) from exc
    if session_date is not None and end < session_date:
        raise serializers.ValidationError(
            {"recurrence_rule": "Serienende darf nicht vor dem ursprünglichen Termin liegen."}
        )
    return end


def series_root(session):
    return TrainingSession.objects.get(pk=session.series_parent_id) if session.series_parent_id else session


def lock_series(session):
    """Root first, then children by pk; plan writers only lock their own row."""
    root = TrainingSession.objects.select_for_update().get(pk=series_root(session).pk)
    children = list(root.series_children.select_for_update().order_by("pk"))
    return root, children


def started(session_date, start_time):
    return timezone.make_aware(datetime.combine(session_date, start_time)) <= timezone.now()


def overlapping(session_date, start_time, end_time, department_id, exclude_ids):
    return list(
        TrainingSession.objects.filter(
            date=session_date, department_id=department_id, start_time__lt=end_time, end_time__gt=start_time
        )
        .exclude(pk__in=exclude_ids)
        .exclude(status=TrainingSession.Status.CANCELLED)
        .order_by("start_time", "pk")
    )


def preview_token(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def generation_preview(root, children, data, user):
    if not can_manage_training_department(user, root.department_id):
        raise serializers.ValidationError({"series": "Keine Schreibberechtigung für die Serienabteilung."})
    if not root.recurrence_rule:
        raise serializers.ValidationError({"recurrence_rule": "Die Serie benötigt eine Wiederholungsregel."})
    anchor = root.original_date or root.date
    end = validate_recurrence_rule(root.recurrence_rule, anchor)
    frequency = root.recurrence_rule["frequency"]
    start = data.get("window_start") or max(anchor, timezone.localdate())
    limit = add_months(start, MAX_MONTHS)
    stop = data.get("window_end") or min(end, limit)
    if stop < start or stop > limit:
        raise serializers.ValidationError(
            {"window_end": f"Vorschaufenster benötigt ein Ende nach Beginn und höchstens {MAX_MONTHS} Monate."}
        )
    stop = min(stop, end)
    duration = validate_session_times(root.start_time, root.end_time)
    for block in root.blocks.all():
        validate_block_times(block.start_offset_minutes, block.duration_minutes, duration)

    existing = {}
    for session in [root, *children]:
        existing.setdefault(session.original_date or session.date, []).append(session)
    series_ids = [session.pk for session in [root, *children]]
    if frequency == "MONTHLY":
        index = max(1, (start.year - anchor.year) * 12 + start.month - anchor.month - 1)
    else:
        index = max(1, (start - anchor).days // (7 if frequency == "WEEKLY" else 14))
    occurrences = []
    while (current := occurrence_date(anchor, frequency, index)) <= stop:
        index += 1
        if current < start:
            continue
        matches = existing.get(current, [])
        visible = all(can_manage_training_department(user, item.department_id) for item in matches)
        if len(matches) > 1 or not visible:
            action, reason = "conflict", "Mehrfache oder nicht bearbeitbare Zuordnung; bleibt unverändert."
        elif matches:
            moved = matches[0].date != current
            action = "preserved"
            reason = "Verschobener Einzeltermin bleibt erhalten." if moved else "Vorhandener Termin bleibt unverändert."
        elif started(current, root.start_time):
            action, reason = "skipped", "Vergangener Termin wird nicht nachträglich erzeugt."
        else:
            action, reason = "new", "Eigenständiger Entwurf mit dem aktuellen Ablauf."
        row = {
            "date": current.isoformat(),
            "action": action,
            "session_id": matches[0].pk if len(matches) == 1 and visible else None,
            "actual_date": matches[0].date.isoformat() if len(matches) == 1 and visible else None,
            "reason": reason,
            "warnings": [],
        }
        if action == "new":
            for other in overlapping(current, root.start_time, root.end_time, root.department_id, series_ids):
                row["warnings"].append(
                    f"Überschneidung mit „{other.title}“ ({other.start_time:%H:%M}–{other.end_time:%H:%M})."
                )
        occurrences.append(row)
        if len(occurrences) > MAX_OCCURRENCES:
            raise serializers.ValidationError(
                {"window_end": f"Höchstens {MAX_OCCURRENCES} Vorkommen je Aktion; Fenster verkürzen."}
            )
    fingerprint = {
        "root": [root.pk, root.revision, root.recurrence_rule],
        "sessions": sorted((child.pk, child.revision, child.date) for child in children),
        "start": start,
        "end": stop,
        "occurrences": occurrences,
    }
    counts = {
        name: sum(row["action"] == name for row in occurrences) for name in ("new", "preserved", "skipped", "conflict")
    }
    return {
        "series_id": str(root.series_uuid) if root.series_uuid else None,
        "root_id": root.pk,
        "root_revision": root.revision,
        "frequency": frequency,
        "anchor_date": anchor.isoformat(),
        "window_start": start.isoformat(),
        "window_end": stop.isoformat(),
        "preview_token": preview_token(fingerprint),
        "occurrences": occurrences,
        "counts": counts,
    }


@transaction.atomic
def generate_missing(root, children, data, user):
    """Returns (result, preview); result is None when the preview is outdated."""
    preview = generation_preview(root, children, data, user)
    if data.get("preview_token") != preview["preview_token"]:
        return None, preview
    if not root.series_uuid:
        root.series_uuid = uuid.uuid4()
        root.original_date = root.original_date or root.date
        root.series_baseline_hash = snapshot_hash(root)
        root.save(update_fields=["series_uuid", "original_date", "series_baseline_hash"])
    created = []
    with copied_files() as files:
        for row in preview["occurrences"]:
            if row["action"] != "new":
                continue
            target = date.fromisoformat(row["date"])
            child = copy_session(
                root, target, user, files, series_parent=root, series_uuid=root.series_uuid, original_date=target
            )
            child.series_baseline_hash = snapshot_hash(child)
            child.save(update_fields=["series_baseline_hash"])
            created.append(child.pk)
    return {"created": len(created), "session_ids": created}, preview
