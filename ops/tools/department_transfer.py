"""Department transfer engine, run by jfctl inside Django's management shell.

Kept in the operations bundle so both runtime adapters can use it without an
application image replacement. All output is aggregate data, never person names.
"""

import hashlib
import json

from django.apps import apps
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.db.models import F

AREAS = {
    "members": ("members.Member",),
    "groups": ("members.Group",),
    "lists": ("members.MemberList",),
    "events": ("members.EventType",),
    "services": ("servicebook.Service",),
    "training": ("training.TrainingSession",),
    "templates": ("training.TrainingTemplate",),
    "email": ("members.EmailMessage",),
    "inventory": ("inventory.Item", "inventory.StorageLocation"),
    "orders": ("orders.Order",),
}
# Relations whose departmental owners must agree. Child records are preserved
# by identity; their scope follows the parent, without copying or rewriting.
EDGES = (
    ("members.Member", "group", "members.Member", "members.Group"),
    ("members.MemberListEntry", "member", "members.MemberList", "members.Member"),
    ("servicebook.Attendance", "person", "servicebook.Service", "members.Member"),
    ("servicebook.Service", "training_session", "servicebook.Service", "training.TrainingSession"),
    ("training.TrainingSession", "series_parent", "training.TrainingSession", "training.TrainingSession"),
    ("training.TrainingSession", "groups", "training.TrainingSession", "members.Group"),
    ("training.TrainingBlock", "groups", "training.TrainingSession", "members.Group"),
    ("training.TrainingTemplate", "groups", "training.TrainingTemplate", "members.Group"),
    ("training.TrainingTemplateBlock", "groups", "training.TrainingTemplate", "members.Group"),
    ("members.Event", "type", "members.Member", "members.EventType"),
    ("participation.Registration", "member", "training.TrainingSession", "members.Member"),
)
OWNER_FIELDS = {
    "members.MemberListEntry": "member_list_id",
    "servicebook.Attendance": "service_id",
    "training.TrainingBlock": "session_id",
    "training.TrainingTemplateBlock": "template_id",
    "members.Event": "member_id",
    "participation.Registration": "session_id",
}


def model(label):
    return apps.get_model(label)


def department(code, *, target=False, create_name=None):
    if code == "global":
        if create_name:
            raise CommandError("Global kann nicht angelegt werden.")
        return None
    Department = model("departments.Department")
    obj = Department.objects.filter(code=code).first()
    if obj:
        if not obj.is_active:
            raise CommandError("Abteilung ist nicht aktiv.")
        if create_name and obj.name != create_name:
            raise CommandError("Zielkürzel existiert mit anderem Namen.")
        return obj
    if target and create_name:
        from django.core.exceptions import ValidationError

        obj = Department(code=code, name=create_name)
        try:
            obj.full_clean()
        except ValidationError as exc:
            raise CommandError("Ungültige Zielabteilung.") from exc
        return obj
    raise CommandError(f"Abteilung {code!r} fehlt (Kürzel aus departments list verwenden).")


def build_plan(source, target, areas, create_name=None):
    areas = sorted(set(areas.split(",")))
    if not areas or set(areas) - AREAS.keys():
        raise CommandError("Bereiche explizit als Kommaliste wählen: " + ",".join(AREAS))
    if source == target:
        raise CommandError("Quelle und Ziel müssen verschieden sein.")
    src = department(source)
    dst = department(target, target=True, create_name=create_name)
    src_id = src.pk if src else None
    dst_scope = dst.pk if dst and dst.pk else ("new-target" if dst else None)
    selected = {}
    for area in areas:
        for label in AREAS[area]:
            cls = model(label)
            if label == "members.Member":
                qs = cls.objects.filter(departments=src_id) if src_id else cls.objects.filter(departments__isnull=True)
            else:
                qs = cls.objects.filter(department_id=src_id)
            selected[label] = set(qs.values_list("pk", flat=True))

    # Build effective ownership before/after. Include non-selected rows to catch
    # incoming references and shared groups, not just outgoing dependencies.
    before, after, snapshot = {}, {}, []
    labels = {label for values in AREAS.values() for label in values}
    for label in sorted(labels):
        cls = model(label)
        before[label], after[label] = {}, {}
        if label == "members.Member":
            rows = cls.objects.order_by("pk").values_list("pk", "departments__pk")
            for pk, dep in rows:
                before[label].setdefault(pk, set()).add(dep)
            for pk, deps in before[label].items():
                deps = deps - {None} or {None}
                before[label][pk] = deps
                effective = set(deps)
                if pk in selected.get(label, set()):
                    effective.discard(src_id)
                    effective.add(dst_scope)
                after[label][pk] = effective
                snapshot.append([label, pk, sorted(str(d) for d in deps)])
        else:
            for pk, dep in cls.objects.order_by("pk").values_list("pk", "department_id"):
                before[label][pk] = {dep}
                after[label][pk] = {dst_scope} if pk in selected.get(label, set()) else {dep}
                snapshot.append([label, pk, dep])

    conflicts = []
    for label, relation, owner, other in EDGES:
        owner_field = OWNER_FIELDS.get(label, "pk")
        for pk, left, right in model(label).objects.order_by("pk").values_list("pk", owner_field, f"{relation}__pk"):
            snapshot.append([label, relation, pk, left, right])
            if left is None or right is None:
                continue
            changed = left in selected.get(owner, set()) or right in selected.get(other, set())
            if not changed:
                continue
            # Global EventTypes remain usable as shared catalog entries.
            if other == "members.EventType" and after[other][right] == {None}:
                continue
            if not after[owner][left] & after[other][right]:
                conflicts.append(f"{label} #{pk}: {owner}/{other}; verknüpfte Bereiche zusammen wählen.")

    # Inventory scope is derived through items/variants. Shared central items
    # may stay global when exercises move, but moving an item away from users
    # in another department must not leave inaccessible material references.
    for label, item_paths, location_paths in (
        ("inventory.Stock", ("item_id", "item_variant__parent_item_id"), ("location_id",)),
        ("inventory.Transaction", ("item_id", "item_variant__parent_item_id"), ("source_id", "target_id")),
    ):
        fields = ("pk", *item_paths, *location_paths)
        for row in model(label).objects.order_by("pk").values_list(*fields):
            pk, item, variant_item, *locations = row
            item = item or variant_item
            snapshot.append([label, *row])
            for location in locations:
                if item is None or location is None:
                    continue
                changed = item in selected.get("inventory.Item", set()) or location in selected.get(
                    "inventory.StorageLocation", set()
                )
                if not changed or after["inventory.Item"][item] & after["inventory.StorageLocation"][location]:
                    continue
                personal = model("inventory.StorageLocation").objects.filter(pk=location, is_member=True).exists()
                if not (personal and after["inventory.StorageLocation"][location] == {None}):
                    conflicts.append(f"{label} #{pk}: Artikel und Lagerort würden verschiedene Abteilungen erhalten.")
    for pk, item, variant_item, session, template in (
        model("training.TrainingBlockMaterial")
        .objects.order_by("pk")
        .values_list("pk", "item_id", "variant__parent_item_id", "block__session_id", "template_block__template_id")
    ):
        snapshot.append(["material", pk, item, variant_item, session, template])
        item = item or variant_item
        owner = "training.TrainingSession" if session else "training.TrainingTemplate"
        owner_id = session or template
        if item is None or owner_id is None:
            continue
        changed = item in selected.get("inventory.Item", set()) or owner_id in selected.get(owner, set())
        if (
            changed
            and after["inventory.Item"][item] != {None}
            and not after["inventory.Item"][item] & after[owner][owner_id]
        ):
            conflicts.append(f"Material #{pk}: Artikel gehört nach Umzug zu einer fremden Abteilung.")

    # Resolved legacy lists carry a second explicit department identity. Refuse
    # rather than silently invalidate the stable legacy resolution mapping.
    ListMap = model("members.MemberListLegacyTarget")
    list_ids = selected.get("members.MemberList", set())
    if (
        ListMap.objects.filter(source_id__in=list_ids).exists()
        or ListMap.objects.filter(target_id__in=list_ids).exists()
    ):
        conflicts.append("Listen mit Altlisten-Zielzuordnung müssen separat fachlich geklärt werden.")

    inbox = model("notifications.InboxItem")
    inbox_ids = set()
    for label, ids in selected.items():
        inbox_ids.update(
            inbox.objects.filter(object_type=label.lower(), object_id__in=ids).values_list("pk", flat=True)
        )
    # Child-owned inbox tasks (requests and registrations) follow the moved owner.
    for label, path, owner in (
        ("portal.ChangeRequest", "target_member_id", "members.Member"),
        ("participation.Registration", "session_id", "training.TrainingSession"),
    ):
        cls = model(label)
        if path not in {f.attname for f in cls._meta.fields}:
            continue
        ids = cls.objects.filter(**{path + "__in": selected.get(owner, set())}).values_list("pk", flat=True)
        inbox_ids.update(
            inbox.objects.filter(object_type=label.lower(), object_id__in=ids).values_list("pk", flat=True)
        )
    snapshot.extend(list(inbox.objects.filter(pk__in=inbox_ids).order_by("pk").values_list("pk", "department_id")))
    digest = hashlib.sha256(
        json.dumps([source, target, src_id, dst_scope, create_name, areas, snapshot], default=str).encode()
    ).hexdigest()
    counts = {label: len(ids) for label, ids in selected.items()}
    counts["notifications.InboxItem"] = len(inbox_ids)
    return (
        {
            "source": source,
            "target": target,
            "areas": areas,
            "create_target": bool(dst and not dst.pk),
            "counts": counts,
            "conflicts": sorted(set(conflicts)),
            "fingerprint": digest,
            "note": "IDs/Eltern/Qualifikationen/Anwesenheiten/Teilnahme/Dateien bleiben erhalten; Rollen und globale Kataloge unverändert.",
        },
        src,
        dst,
        selected,
        inbox_ids,
    )


def invariant_hashes(selected, inbox_ids, new_code):
    """Hash raw PostgreSQL rows, including legacy tables, without disclosing data.

    Only intentional ownership fields and changed member membership rows are
    excluded. Comparing inside the transaction makes an integrity failure roll
    back before web access is released. Raw SQL also keeps encrypted values raw.
    """
    if connection.vendor != "postgresql":
        return None
    omitted = {}
    for label in selected:
        if label != "members.Member":
            omitted[model(label)._meta.db_table] = ["department_id"]
    if "members.MemberList" in selected:
        omitted[model("members.MemberList")._meta.db_table].append("organization_wide")
    if "training.TrainingSession" in selected:
        omitted[model("training.TrainingSession")._meta.db_table].append("revision")
    if inbox_ids:
        omitted[model("notifications.InboxItem")._meta.db_table] = ["department_id"]
    member_table = model("members.Member").departments.through._meta.db_table
    department_table = model("departments.Department")._meta.db_table
    result = {}
    with connection.cursor() as cursor:
        tables = sorted(connection.introspection.table_names(cursor))
        for table in tables:
            query = "SELECT (to_jsonb(t) - %s::text[])::text FROM " + connection.ops.quote_name(table) + " AS t"
            params = [omitted.get(table, [])]
            if table == member_table:
                query += " WHERE NOT (member_id = ANY(%s))"
                params.append(sorted(selected.get("members.Member", set())))
            elif table == department_table and new_code:
                query += " WHERE code <> %s"
                params.append(new_code)
            cursor.execute(query + " ORDER BY 1", params)
            digest, count = hashlib.sha256(), 0
            while rows := cursor.fetchmany(1000):
                for row in rows:
                    digest.update(row[0].encode())
                    digest.update(b"\n")
                    count += 1
            result[table] = (count, digest.hexdigest())
    return result


def run_transfer(source, target, areas, create_name=None, apply=False, expect=None):
    with transaction.atomic():
        if apply and connection.vendor == "postgresql":
            # A maintenance window stops web/workers; transaction-level locks
            # also serialize CLI transfers and protect dependency reads/writes.
            tables = sorted({m._meta.db_table for m in apps.get_models(include_auto_created=True) if m._meta.managed})
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '10s'")
                cursor.execute(
                    "LOCK TABLE "
                    + ",".join(connection.ops.quote_name(t) for t in tables)
                    + " IN SHARE ROW EXCLUSIVE MODE"
                )
        plan, src, dst, selected, inbox_ids = build_plan(source, target, areas, create_name)
        if not apply:
            return plan
        if plan["conflicts"]:
            raise CommandError("Abhängigkeiten verhindern Umzug: " + "; ".join(plan["conflicts"][:20]))
        if not expect or expect != plan["fingerprint"]:
            raise CommandError("Vorschau fehlt oder ist veraltet; neue Vorschau erstellen.")
        new_code = dst.code if dst and not dst.pk else None
        invariant_before = invariant_hashes(selected, inbox_ids, new_code)
        if dst and not dst.pk:
            dst.save()
        dst_id = dst.pk if dst else None
        Member = model("members.Member")
        for label, ids in selected.items():
            if label == "members.Member":
                through = Member.departments.through
                if src:
                    through.objects.filter(member_id__in=ids, department_id=src.pk).delete()
                if dst:
                    through.objects.bulk_create(
                        [through(member_id=pk, department_id=dst_id) for pk in sorted(ids)], ignore_conflicts=True
                    )
            else:
                updates = {"department_id": dst_id}
                if label == "members.MemberList":
                    updates["organization_wide"] = dst is None
                if label == "training.TrainingSession":
                    updates["revision"] = F("revision") + 1
                model(label).objects.filter(pk__in=ids).update(**updates)
        # Only rescope tasks tied to an explicitly moved object. Recipient lists
        # are preserved; the inbox rechecks department rights on every read.
        model("notifications.InboxItem").objects.filter(pk__in=inbox_ids).update(department_id=dst_id)
        invariant_after = invariant_hashes(selected, inbox_ids, new_code)
        if invariant_before != invariant_after:
            raise CommandError("Datenvergleich fehlgeschlagen; gesamter Umzug zurückgerollt.")
        plan["verified_tables"] = len(invariant_after) if invariant_after is not None else None
        plan["applied"] = True
        return plan


def list_departments():
    return list(model("departments.Department").objects.order_by("code").values("code", "name", "is_active"))
