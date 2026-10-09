"""Change request notifications (PORTAL-03.4, concept 4.9.1).

- Submitted or updated: one open task per request for reviewers in the person's
  departments (D9), a mail per version with "Prüfen" and "Alle übernehmen".
- Decided: notice and mail to the requesting portal account; reviewer tasks close.
- Withdrawn: reviewer tasks close without a mail.
Titles carry only the person's name, never requested values (privacy on lock screens).
"""

from django.utils import timezone

from .dispatch import common_context, queue_email, queue_push
from .inbox import complete_tasks, notify, staff_with_permission
from .models import InboxItem, InboxRecipient

REVIEW = "portal.review_changerequest"
RESULTS = {"applied": "übernommen", "partial": "teilweise übernommen", "rejected": "abgelehnt"}
DECISIONS = {"apply": "übernommen", "reject": "abgelehnt"}


def review_route(change_request):
    return f"/portal-verwaltung?tab=antraege&antrag={change_request.pk}"


def _reviewers(change_request):
    from portal.change_requests import own_request, target_record
    from portal.invitations import record_department_ids

    departments = sorted(record_department_ids(target_record(change_request)))
    users = {}
    for department_id in departments:
        for user in staff_with_permission(REVIEW, department_id):
            users[user.pk] = user
    return departments, [u for u in users.values() if not own_request(change_request, u)]


def _person_name(record):
    return record.get_full_name()


def change_request_submitted(change_request_id):
    from portal.change_requests import payload
    from portal.models import ChangeRequest

    from .actions import make_link

    change = ChangeRequest.objects.select_related("requested_by").filter(pk=change_request_id).first()
    if change is None or change.status != ChangeRequest.Status.OPEN:
        return None
    data = payload(change, with_current=True)
    departments, reviewers = _reviewers(change)
    if not reviewers:
        return None
    title = f"Änderungsantrag für {data['person_name']}"
    task = InboxItem.objects.filter(
        kind="cr_submitted",
        item_type=InboxItem.ItemType.TASK,
        task_state=InboxItem.TaskState.OPEN,
        object_type="portal.changerequest",
        object_id=change.pk,
    ).first()
    if task is None:
        task = notify(
            kind="cr_submitted",
            category=InboxItem.Category.REQUESTS,
            item_type=InboxItem.ItemType.TASK,
            title=title,
            department=departments[0] if departments else None,
            obj=change,
            permission=REVIEW,
            link=review_route(change),
            recipients=reviewers,
        )
    else:  # a new version: the same task shows up as unread again
        InboxItem.objects.filter(pk=task.pk).update(title=title, updated_at=timezone.now())
        InboxRecipient.objects.filter(item=task).update(read_at=None, hidden_at=None)
    requester = change.requested_by
    rows = [{"label": f["label"], "old": f["old"], "new": f["new"]} for f in data["fields"]]
    conflicts = sum(1 for f in data["fields"] if f["conflict"])
    for user in reviewers:
        review_url = make_link(user, "cr_review", {"c": change.pk})
        actions = [{"label": "Prüfen", "url": review_url, "style": "primary"}]
        if not conflicts:
            actions.append(
                {
                    "label": "Alle übernehmen",
                    "url": make_link(user, "cr_apply", {"c": change.pk, "v": change.version}),
                    "style": "secondary",
                }
            )
        context = {
            **common_context(user, open_url=review_url, actions=actions),
            "request": {
                "person_name": data["person_name"],
                "requested_by": (requester.get_full_name() or requester.username) if requester else "",
                "fields": rows,
                "conflicts": conflicts,
            },
        }
        queue_email("cr_submitted", user, context, event_key=f"cr_submitted:{change.pk}:{change.version}:{user.pk}")
        queue_push(user, task, "requests")
    return task


def change_request_closed(change_request_id, by=None):
    """Close reviewer tasks; tell the requester about a decision (not about a withdrawal)."""
    from portal.change_requests import payload
    from portal.models import ChangeRequest

    from .actions import make_link

    change = ChangeRequest.objects.select_related("requested_by").filter(pk=change_request_id).first()
    if change is None:
        return None
    complete_tasks(change, kind="cr_submitted", by=by)
    requester = change.requested_by
    if change.status not in RESULTS or requester is None or not requester.is_active:
        return None
    data = payload(change)
    result = RESULTS[change.status]
    item = notify(
        kind="cr_decided",
        category=InboxItem.Category.PARTICIPATION if requester.is_portal_account else InboxItem.Category.REQUESTS,
        title=f"Änderungsantrag für {data['person_name']}: {result}",
        obj=change,
        link="/portal/daten" if requester.is_portal_account else "/",
        recipients=[requester],
    )
    open_url = make_link(requester, "open", {"r": "/portal/daten" if requester.is_portal_account else "/"})
    context = {
        **common_context(
            requester, open_url=open_url, actions=[{"label": "Daten ansehen", "url": open_url, "style": "primary"}]
        ),
        "request": {
            "person_name": data["person_name"],
            "result": result,
            "fields": [
                {
                    "label": f["label"],
                    "old": f["old"],
                    "new": f["new"],
                    "decision": DECISIONS.get(f.get("decision"), ""),
                }
                for f in data["fields"]
            ],
            "note": change.decision_note,
        },
    }
    queue_email("cr_decided", requester, context, event_key=f"cr_decided:{change.pk}")
    queue_push(requester, item, "participation")
    return item
