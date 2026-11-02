"""Consents changed in the portal: the responsible youth directors are told (inbox, mail, push).

Recipients hold the DSGVO right ``members.anonymize_member`` in one of the child's
departments; in the role catalog that is the (department) youth director. Titles
name the child and the kind of consent, nothing else.
"""

from .actions import make_link
from .dispatch import common_context, queue_email, queue_push
from .inbox import notify, staff_with_permission
from .models import InboxItem

RESPONSIBLE = "members.anonymize_member"


def consent_changed(record_id):
    from privacy.models import ConsentKind, ConsentRecord

    record = ConsentRecord.objects.select_related("member", "recorded_by").filter(pk=record_id).first()
    if record is None or record.member is None:
        return None
    member = record.member
    departments = list(member.departments.values_list("pk", flat=True)) or [None]
    users = {}
    for department_id in departments:
        for user in staff_with_permission(RESPONSIBLE, department_id):
            users[user.pk] = user
    if not users:
        return None
    kind = ConsentKind.objects.filter(slug=record.kind).first()
    label = kind.label if kind else record.kind
    granted = record.status == ConsentRecord.Status.GRANTED
    verb = "erteilt" if granted else "widerrufen"
    name = f"{member.name} {member.lastname}".strip()
    route = f"/members/{member.pk}"
    item = notify(
        kind="consent_changed",
        category=InboxItem.Category.REQUESTS,
        title=f"Einwilligung {verb}: {label} für {name}",
        department=departments[0],
        obj=member,
        permission=RESPONSIBLE,
        link=route,
        recipients=list(users.values()),
    )
    by = record.recorded_by
    for user in users.values():
        open_url = make_link(user, "open", {"r": route})
        context = {
            **common_context(
                user, open_url=open_url, actions=[{"label": "Mitglied öffnen", "url": open_url, "style": "primary"}]
            ),
            "consent": {
                "person_name": name,
                "kind": label,
                "status": verb,
                "by": (by.get_full_name() or by.username) if by else "",
                "date": record.recorded_at.strftime("%d.%m.%Y"),
            },
        }
        # Default channels: superusers only get mail/push if they opted in (as for change requests).
        queue_email("consent_changed", user, context, event_key=f"consent_changed:{record.pk}:{user.pk}")
        queue_push(user, item, "requests")
    return item
