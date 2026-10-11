"""Own records of linked staff accounts (PORTAL-04.3, E14, Q4).

- Master data of the own member record (and of the own parent record and its
  children) stays editable with the existing rights; every such change is
  logged as "Eigenänderung" in ``ChangeLog``.
- Qualifications and special tasks of the own member record, of the own
  children and of the own account (``Qualification.user``) are created, changed
  and deleted by another person (four-eyes): the API answers 403 with a reason.

The lock already applies while a link is pending: otherwise an account could
delay its confirmation to edit its own evidence. Rejected links do not count.
"""

from rest_framework.exceptions import PermissionDenied

from .models import AccountLink, ChangeLog

OWN_RECORD_CODE = "own_record"
OWN_RECORD_DETAIL = "Eigene Qualifikationen und Sonderaufgaben pflegt eine andere Person (Vier-Augen-Prinzip)."


def _link(user):
    if not (user and user.is_authenticated) or getattr(user, "is_portal_account", False):
        return None
    return (
        AccountLink.objects.exclude(status=AccountLink.Status.REJECTED)
        .only("member_id", "parent_id", "status")
        .filter(user=user)
        .first()
    )


def own_member_ids(user):
    """Own member record plus all children of the own parent record (any age: the four-eyes rule stays)."""
    link = _link(user)
    if link is None:
        return set()
    ids = {link.member_id} if link.member_id else set()
    if link.parent_id:
        from members.models import Member

        ids |= set(Member.objects.filter(parent__pk=link.parent_id).values_list("pk", flat=True))
    return ids


def is_linked(user):
    return _link(user) is not None


def deny_own_evidence(user, *, member_id=None, person_user_id=None):
    """Raise 403 with reason when ``user`` would change evidence about themselves or their children."""
    link = _link(user)
    if link is None:
        return
    if (person_user_id is not None and person_user_id == user.pk) or (
        member_id is not None and member_id in own_member_ids(user)
    ):
        raise PermissionDenied({"detail": OWN_RECORD_DETAIL, "code": OWN_RECORD_CODE})


def is_own_record(user, record):
    """Member (own or own child) or the own parent record."""
    from members.models import Parent

    link = _link(user)
    if link is None:
        return False
    if isinstance(record, Parent):
        return record.pk == link.parent_id
    return record.pk in own_member_ids(user)


# Fields logged with their values; free texts are only marked as changed.
LOGGED_FIELDS = (
    "name",
    "lastname",
    "gender",
    "birthday",
    "joined",
    "street",
    "zip_code",
    "city",
    "phone",
    "mobile",
    "email",
    "email2",
    "identityCardNumber",
    "canSwimm",
    "status",
    "group",
)
VALUE_HIDDEN = ("notes",)


def snapshot(record):
    values = {}
    for field in LOGGED_FIELDS + VALUE_HIDDEN:
        if not hasattr(record, field) and not hasattr(record, f"{field}_id"):
            continue
        try:
            value = getattr(record, field)
        except Exception:  # missing related object
            value = None
        values[field] = "" if value is None else str(value)
    return values


def log_self_change(user, record, before):
    """Write one ``ChangeLog`` row per changed field when ``user`` edited an own record (E14)."""
    from members.models import Parent

    if not is_own_record(user, record):
        return 0
    after = snapshot(record)
    kind = "parent" if isinstance(record, Parent) else "member"
    rows = []
    for field, old in before.items():
        new = after.get(field, "")
        if old == new:
            continue
        if field in VALUE_HIDDEN:
            old, new = "", "(geändert)"
        rows.append(
            ChangeLog(
                target_kind=kind,
                target_id=record.pk,
                field=field[:30],
                old=old[:300],
                new=new[:300],
                applied_by=user,
                self_change=True,
            )
        )
    ChangeLog.objects.bulk_create(rows)
    return len(rows)


def change_log(kind, record_id, limit=50):
    return (
        ChangeLog.objects.filter(target_kind=kind, target_id=record_id)
        .select_related("applied_by")
        .order_by("-applied_at", "-pk")[:limit]
    )


FIELD_LABELS = {
    "name": "Vorname",
    "lastname": "Nachname",
    "gender": "Geschlecht",
    "birthday": "Geburtsdatum",
    "joined": "Eintritt",
    "street": "Straße",
    "zip_code": "PLZ",
    "city": "Ort",
    "phone": "Telefon",
    "mobile": "Mobil",
    "email": "E-Mail",
    "email2": "Zweite E-Mail",
    "identityCardNumber": "Ausweisnummer",
    "canSwimm": "Schwimmer",
    "status": "Status",
    "group": "Gruppe",
    "notes": "Bemerkungen",
}


def log_payload(row):
    by = row.applied_by
    return {
        "id": row.pk,
        "field": row.field,
        "label": FIELD_LABELS.get(row.field, row.field),
        "old": row.old,
        "new": row.new,
        "applied_by": (by.get_full_name() or by.username) if by else "",
        "applied_at": row.applied_at,
        "self_change": row.self_change,
        "via_request": row.change_request_id is not None,
    }
