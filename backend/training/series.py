"""Bounded, versioned series previews that never erase existing exercises."""

import calendar
import hashlib
import json
import re
import uuid
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from training.api.permissions import can_manage_training_department
from training.api.plan import advance_revision, delete_plan_blocks
from training.api.validation import validate_block_times, validate_session_times
from training.copying import (
    BLOCK_FIELDS,
    SESSION_FIELDS,
    copied_files,
    copy_block,
    copy_session,
    resources,
    snapshot_hash,
)
from training.models import TrainingSession
from training.workflow import linked_service, service_is_documented, sync_linked_service

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


class PropagationInputSerializer(serializers.Serializer):
    include_deviating = serializers.ListField(
        child=serializers.IntegerField(), required=False, max_length=MAX_OCCURRENCES
    )
    preview_token = serializers.CharField(required=False, max_length=64)


def comparable(session):
    """Plan content without per-copy media URLs, for a readable change summary."""
    blocks = [
        {
            **{name: getattr(block, name) for name in BLOCK_FIELDS if name != "content"},
            "content": re.sub(r'src="[^"]*"', "", block.content),
            "groups": sorted(block.groups.values_list("pk", flat=True)),
            **resources(block),
        }
        for block in session.blocks.order_by("start_offset_minutes", "position_order", "pk")
    ]
    return {
        **{name: getattr(session, name) for name in SESSION_FIELDS},
        "groups": sorted(session.groups.values_list("pk", flat=True)),
        "blocks": blocks,
    }


def describe_changes(source, target):
    new, old = comparable(source), comparable(target)
    changes = []
    if new["title"] != old["title"]:
        changes.append(f"Titel: „{old['title']}“ → „{new['title']}“")
    if (new["start_time"], new["end_time"]) != (old["start_time"], old["end_time"]):
        changes.append(
            f"Zeit: {old['start_time']:%H:%M}–{old['end_time']:%H:%M} → {new['start_time']:%H:%M}–{new['end_time']:%H:%M}"
        )
    if new["location"] != old["location"]:
        changes.append("Ort")
    if (new["description"], new["notes"]) != (old["description"], old["notes"]):
        changes.append("Beschreibung/Notizen")
    if new["groups"] != old["groups"]:
        changes.append("Gruppen")
    if new["blocks"] != old["blocks"]:
        changes.append(f"Ablauf: {len(old['blocks'])} → {len(new['blocks'])} Bausteine")
    return changes


def is_deviating(session):
    moved = session.original_date is not None and session.date != session.original_date
    # Without a baseline (legacy series) a plan is conservatively treated as deviating.
    return moved or not session.series_baseline_hash or snapshot_hash(session) != session.series_baseline_hash


def propagation_preview(source, root, children, data, user):
    if not source.series_uuid:
        raise serializers.ValidationError({"series": "Dieser Termin gehört zu keiner gespeicherten Serie."})
    if not can_manage_training_department(user, source.department_id):
        raise serializers.ValidationError({"series": "Keine Schreibberechtigung für diesen Termin."})
    position = source.original_date or source.date
    include = set(data.get("include_deviating") or [])
    rows = []
    for target in sorted(
        (s for s in [root, *children] if s.pk != source.pk and (s.original_date or s.date) > position),
        key=lambda s: (s.original_date or s.date, s.pk),
    ):
        row = {
            "session_id": target.pk,
            "date": target.date.isoformat(),
            "original_date": (target.original_date or target.date).isoformat(),
            "title": target.title,
            "status": target.status,
            "changes": [],
            "overridable": False,
        }
        if not can_manage_training_department(user, target.department_id):
            row.update(
                session_id=None,
                title="Nicht sichtbarer Termin",
                action="conflict",
                reason="Keine Schreibberechtigung; bleibt unverändert.",
            )
        elif target.department_id != source.department_id:
            row.update(action="conflict", reason="Andere Abteilung; bleibt unverändert.")
        elif target.status in (TrainingSession.Status.COMPLETED, TrainingSession.Status.CANCELLED):
            row.update(action="history", reason="Abgeschlossen oder abgesagt; bleibt unverändert.")
        elif started(target.date, target.start_time) or service_is_documented(linked_service(target)):
            row.update(
                action="history", reason="Begonnen oder dokumentiert; Dienst und Anwesenheiten bleiben unverändert."
            )
        else:
            row["changes"] = describe_changes(source, target)
            if not row["changes"]:
                row.update(action="unchanged", reason="Bereits identisch.")
            elif is_deviating(target):
                row["overridable"] = True
                chosen = target.pk in include
                row.update(
                    action="update" if chosen else "deviating",
                    reason="Abweichender Einzeltermin – ausdrücklich zum Überschreiben ausgewählt."
                    if chosen
                    else "Abweichender Einzeltermin bleibt standardmäßig erhalten.",
                )
            else:
                row.update(action="update", reason="Wird auf den Stand dieses Termins gebracht.")
        rows.append(row)
    unknown = include - {row["session_id"] for row in rows if row["overridable"]}
    if unknown:
        raise serializers.ValidationError({"include_deviating": "Nur abweichende, änderbare Folgetermine auswählbar."})
    if len(rows) > MAX_OCCURRENCES:
        raise serializers.ValidationError({"series": f"Höchstens {MAX_OCCURRENCES} Vorkommen je Aktion."})
    fingerprint = {
        "source": [source.pk, source.revision],
        "targets": sorted((target.pk, target.revision, target.date, target.status) for target in [*children, root]),
        "include": sorted(include),
        "rows": rows,
    }
    counts = {name: sum(row["action"] == name for row in rows) for name in ACTIONS}
    return {
        "source_id": source.pk,
        "source_revision": source.revision,
        "preview_token": preview_token(fingerprint),
        "occurrences": rows,
        "counts": counts,
    }


ACTIONS = ("update", "unchanged", "deviating", "history", "conflict")


def replace_plan(target, source, user, files):
    for name in SESSION_FIELDS:
        setattr(target, name, getattr(source, name))
    target.save()
    target.groups.set(source.groups.all())
    delete_plan_blocks(target.blocks.all())
    for block in source.blocks.all():
        copy_block(block, user, files, session=target)
    advance_revision(target)
    sync_linked_service(target)
    target.series_baseline_hash = snapshot_hash(target)
    target.save(update_fields=["series_baseline_hash"])


@transaction.atomic
def propagate(source, root, children, data, user):
    """Returns (result, preview); result is None when the preview is outdated."""
    source = next(s for s in [root, *children] if s.pk == source.pk)
    preview = propagation_preview(source, root, children, data, user)
    if data.get("preview_token") != preview["preview_token"]:
        return None, preview
    by_id = {s.pk: s for s in [root, *children]}
    updated = []
    with copied_files() as files:
        for row in preview["occurrences"]:
            if row["action"] == "update":
                replace_plan(by_id[row["session_id"]], source, user, files)
                updated.append(row["session_id"])
    # This occurrence is now the agreed state of the following series.
    source.series_baseline_hash = snapshot_hash(source)
    source.save(update_fields=["series_baseline_hash"])
    return {"updated": len(updated), "session_ids": updated}, preview
