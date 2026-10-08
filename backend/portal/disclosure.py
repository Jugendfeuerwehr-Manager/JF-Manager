"""What a portal account sees about a person (PORTAL-02.2).

Every field is listed positively per category; nothing is serialised by
exclusion. Notes, events, attachments, attendance and issuer/notes of
qualifications are never read here.
"""

from django.utils import timezone

from members.models import Parent

from .policy import PolicySet, age_on


def _date(value):
    return value.isoformat() if value else None


def contact(member):
    return {
        "first_name": member.name,
        "last_name": member.lastname,
        "street": member.street,
        "zip_code": member.zip_code,
        "city": member.city,
        "phone": member.phone,
        "mobile": member.mobile,
        "email": member.email,
    }


def parent_contact(parent):
    return {
        "first_name": parent.name,
        "last_name": parent.lastname,
        "street": parent.street,
        "zip_code": parent.zip_code,
        "city": parent.city,
        "phone": parent.phone,
        "mobile": parent.mobile,
        "email": parent.email,
        "email2": parent.email2,
    }


def _group(member, policies, audience, department_ids):
    shown = [d for d in department_ids if policies.department_value(d, "group", audience) == "visible"]
    group = member.group if member.group_id and member.group.department_id in [*shown, None] else None
    return {
        "group": group.name if group else None,
        "departments": sorted(d.name for d in member.departments.all() if d.pk in shown),
    }


def _qualifications(member, today):
    rows = member.qualifications.select_related("type").order_by("type__name")
    return [
        {
            "type": q.type.name,
            "acquired": _date(q.date_acquired),
            "expires": _date(q.date_expires),
            "valid": q.date_expires is None or q.date_expires >= today,
        }
        for q in rows
    ]


def _special_tasks(member):
    rows = member.special_tasks.select_related("task").order_by("-start_date")
    return [{"task": t.task.name, "start": _date(t.start_date), "end": _date(t.end_date)} for t in rows]


def _equipment(member):
    location = getattr(member, "personal_storage_location", None)
    if location is None:
        return []
    stocks = location.stock_set.filter(quantity__gt=0).select_related("item", "item_variant")
    return [
        {
            "item": s.item.name if s.item_id else (s.item_variant.item.name if s.item_variant_id else ""),
            "variant": str(s.item_variant) if s.item_variant_id else "",
            "quantity": s.quantity,
        }
        for s in stocks
    ]


def _other_parents(member, viewer_parent):
    others = Parent.objects.filter(children=member).exclude(pk=getattr(viewer_parent, "pk", None))
    return [{"name": p.get_full_name(), "phone": p.phone, "mobile": p.mobile} for p in others.order_by("lastname")]


def person_payload(member, relation, viewer_parent=None, policies=None, today=None):
    """``relation`` is "self" (member account) or "child" (parent account)."""
    policies = policies or PolicySet.load()
    today = today or timezone.localdate()
    audience = "members" if relation == "self" else "parents"
    department_ids = list(member.departments.values_list("pk", flat=True))
    categories = policies.visible_categories(audience, department_ids)
    data = {"id": member.pk, "relation": relation, "categories": categories, "contact": contact(member)}
    if "birthday" in categories and member.birthday:
        data["birthday"] = _date(member.birthday)
        data["age"] = age_on(member.birthday, today)
    if "group" in categories:
        data["group"] = _group(member, policies, audience, department_ids)
    if "membership" in categories:
        data["membership"] = {
            "status": member.status.name if member.status_id else None,
            "joined": _date(member.joined),
        }
    if "identity" in categories:
        data["identity"] = {"card_number": member.identityCardNumber}
    if "swimming" in categories:
        data["swimming"] = {"can_swim": member.canSwimm}
    if "qualifications" in categories:
        data["qualifications"] = _qualifications(member, today)
    if "special_tasks" in categories:
        data["special_tasks"] = _special_tasks(member)
    if "equipment" in categories:
        data["equipment"] = _equipment(member)
    if "other_parents" in categories:
        data["other_parents"] = _other_parents(member, viewer_parent)
    return data


ALLOWED_KEYS = {
    "id",
    "relation",
    "categories",
    "contact",
    "birthday",
    "age",
    "group",
    "membership",
    "identity",
    "swimming",
    "qualifications",
    "special_tasks",
    "equipment",
    "other_parents",
}
