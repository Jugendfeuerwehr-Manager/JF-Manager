"""Planning warnings: overlapping groups, instructors, locations and material shortage.

Warnings never block saving. Publishing despite warnings needs a stored
justification. Exercises the user cannot plan are only mentioned anonymously.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from django.db.models import Q, Sum
from rest_framework import serializers

from inventory.models import Stock
from training.api.permissions import can_manage_training_department
from training.models import TrainingSession

ALL = None  # empty group selection = all groups of the exercise


@dataclass
class PlannedBlock:
    ref: str
    title: str
    start: int  # minutes since midnight
    end: int
    groups: frozenset | None
    instructors: dict = field(default_factory=dict)  # id -> name
    location: str = ""
    materials: list = field(default_factory=list)  # (item_id, variant_id, quantity, label)
    session: TrainingSession | None = None


def minutes(value):
    return value.hour * 60 + value.minute


def normalize_location(value):
    return " ".join((value or "").casefold().split())


def clock(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def person(user):
    return user.get_full_name() or user.username


def saved_blocks(session, ref_prefix=""):
    start = minutes(session.start_time)
    result = []
    for block in session.blocks.all():
        groups = frozenset(group.pk for group in block.groups.all())
        result.append(
            PlannedBlock(
                ref=f"{ref_prefix}{block.pk}",
                title=block.title,
                start=start + block.start_offset_minutes,
                end=start + block.start_offset_minutes + block.duration_minutes,
                groups=groups or ALL,
                instructors={user.pk: person(user) for user in block.instructors.all()},
                location=normalize_location(block.location),
                materials=[(m.item_id, m.variant_id, m.quantity, m.label) for m in block.materials.all()],
                session=session,
            )
        )
    return result


def draft_blocks(prepared):
    """Blocks of a validated, unsaved plan (serializers from ``prepare_plan``)."""
    result = []
    for index, serializer in enumerate(prepared):
        data, instance = serializer.validated_data, serializer.instance
        session = data["session"]

        def value(name, default, data=data, instance=instance):
            return data.get(name, getattr(instance, name, default) if instance is not None else default)

        groups = data.get("groups")
        if groups is None:
            groups = list(instance.groups.all()) if instance is not None else []
        instructors = data.get("instructors")
        if instructors is None:
            instructors = list(instance.instructors.all()) if instance is not None else []
        materials = data.get("materials")
        if materials is None:
            materials = (
                [
                    {"item": m.item, "variant": m.variant, "quantity": m.quantity, "label": m.label}
                    for m in instance.materials.all()
                ]
                if instance is not None
                else []
            )
        start = minutes(session.start_time) + value("start_offset_minutes", 0)
        result.append(
            PlannedBlock(
                ref=str(instance.pk) if instance is not None else f"neu-{index}",
                title=value("title", ""),
                start=start,
                end=start + value("duration_minutes", 15),
                groups=frozenset(group.pk for group in groups) or ALL,
                instructors={user.pk: person(user) for user in instructors},
                location=normalize_location(value("location", "")),
                materials=[
                    (
                        getattr(m.get("item"), "pk", None),
                        getattr(m.get("variant"), "pk", None),
                        m.get("quantity", 1),
                        m.get("label", ""),
                    )
                    for m in materials
                ],
                session=session,
            )
        )
    return result


def overlap(a, b):
    return a.start < b.end and b.start < a.end


def shared_groups(a, b):
    if a.groups is ALL or b.groups is ALL:
        return True
    return bool(a.groups & b.groups)


def available_stock(item_id, variant_id):
    """Stock outside member storage locations; a computed figure, never a reservation."""
    stock = Stock.objects.filter(location__is_member=False)
    if variant_id:
        stock = stock.filter(item_variant_id=variant_id)
    else:
        stock = stock.filter(Q(item_id=item_id) | Q(item_variant__parent_item_id=item_id))
    return stock.aggregate(total=Sum("quantity"))["total"] or 0


def find_conflicts(session, group_names, blocks, user):
    """``session`` describes the prospective exercise (date, times, department)."""
    warnings = []
    seen = set()

    def warn(code, message, refs, other=None):
        key = (code, message)
        if key in seen:
            return
        seen.add(key)
        warnings.append({"code": code, "message": message, "blocks": sorted(set(refs)), "other_session": other})

    def label_groups(a, b):
        if a.groups is ALL and b.groups is ALL:
            return "alle Gruppen"
        common = (a.groups or b.groups) if (a.groups is ALL or b.groups is ALL) else (a.groups & b.groups)
        return ", ".join(sorted(group_names.get(pk, f"Gruppe {pk}") for pk in common))

    # Within the exercise: groups, instructors and locations.
    ordered = sorted(blocks, key=lambda b: (b.start, b.ref))
    for i, a in enumerate(ordered):
        for b in ordered[i + 1 :]:
            if b.start >= a.end:
                break
            span = f"{clock(max(a.start, b.start))}–{clock(min(a.end, b.end))}"
            if shared_groups(a, b):
                warn(
                    "group",
                    f"Gruppenüberschneidung ({label_groups(a, b)}): „{a.title}“ und „{b.title}“, {span}.",
                    [a.ref, b.ref],
                )
            for pk in a.instructors.keys() & b.instructors.keys():
                warn(
                    "instructor",
                    f"{a.instructors[pk]} ist gleichzeitig bei „{a.title}“ und „{b.title}“ eingeplant ({span}).",
                    [a.ref, b.ref],
                )
            if a.location and a.location == b.location:
                warn(
                    "location",
                    f"Ort „{a.location}“ gleichzeitig für „{a.title}“ und „{b.title}“ belegt ({span}).",
                    [a.ref, b.ref],
                )

    # Other exercises on the same day.
    others = (
        TrainingSession.objects.filter(date=session.date)
        .exclude(pk=session.pk)
        .exclude(status=TrainingSession.Status.CANCELLED)
        .prefetch_related("blocks__groups", "blocks__instructors", "blocks__materials")
    )
    foreign = []
    for other in others:
        visible = can_manage_training_department(user, other.department_id)
        described = {"id": other.pk, "title": other.title} if visible else None
        name = f"„{other.title}“" if visible else "einer anderen Übung (nicht sichtbar)"
        other_blocks = saved_blocks(other, ref_prefix=f"x{other.pk}-")
        foreign.extend((block, visible) for block in other_blocks)
        for a in blocks:
            for b in other_blocks:
                if not overlap(a, b):
                    continue
                span = f"{clock(max(a.start, b.start))}–{clock(min(a.end, b.end))}"
                for pk in a.instructors.keys() & b.instructors.keys():
                    warn(
                        "instructor",
                        f"{a.instructors[pk]} ist zur selben Zeit in {name} eingeplant ({span}, „{a.title}“).",
                        [a.ref],
                        described,
                    )
                if a.location and a.location == b.location:
                    warn(
                        "location",
                        f"Ort „{a.location}“ ist zur selben Zeit in {name} belegt ({span}, „{a.title}“).",
                        [a.ref],
                        described,
                    )

    # Computed material shortage at every block start of this exercise.
    demand = defaultdict(list)  # (item, variant) -> [(block, quantity, own, visible)]
    for block in blocks:
        for item, variant, quantity, _label in block.materials:
            if item:
                demand[(item, variant)].append((block, quantity, True, True))
    for block, visible in foreign:
        for item, variant, quantity, _label in block.materials:
            if (item, variant) in demand:
                demand[(item, variant)].append((block, quantity, False, visible))
    for (item, variant), rows in demand.items():
        stock = available_stock(item, variant)
        label = next(row[0] for row in rows if row[2])
        label = next(m[3] for m in label.materials if (m[0], m[1]) == (item, variant))
        worst = None
        for block, _quantity, own, _visible in rows:
            if not own:
                continue
            active = [row for row in rows if row[0].start <= block.start < row[0].end]
            needed = sum(row[1] for row in active)
            if needed > stock and (worst is None or needed > worst[0]):
                worst = (needed, block, active)
        if worst:
            needed, block, active = worst
            refs = [row[0].ref for row in active if row[2]]
            foreign_rows = [row for row in active if not row[2]]
            extra = ""
            if foreign_rows:
                hidden = any(not row[3] for row in foreign_rows)
                extra = " inkl. Bedarf aus anderen Übungen" + (" (teilweise nicht sichtbar)" if hidden else "")
            warn(
                "material",
                f"Material „{label}“: gleichzeitig {needed} benötigt{extra}, rechnerisch {stock} verfügbar (ab {clock(block.start)}).",
                refs,
            )
    return warnings


def require_publish_justification(candidate, was_published, groups, blocks, user, attrs):
    """Publishing with warnings needs a justification; it is stored with the warnings."""
    if candidate.status != TrainingSession.Status.PUBLISHED or was_published:
        return
    warnings = find_conflicts(candidate, {g.pk: g.name for g in groups}, blocks, user)
    justification = (attrs.get("publish_justification") or "").strip()
    if warnings and not justification:
        raise serializers.ValidationError(
            {
                "publish_justification": "Die Übung hat Planungswarnungen. Für die Veröffentlichung eine Begründung angeben.",
                "warnings": [warning["message"] for warning in warnings],
            }
        )
    attrs["publish_warnings"] = [warning["message"] for warning in warnings]
    if not warnings:
        attrs["publish_justification"] = ""
