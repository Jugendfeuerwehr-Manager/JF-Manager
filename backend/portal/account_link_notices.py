"""Notices about staff account links (concept 4.9.1 "Kontoverknüpfung", PORTAL-04).

Pending: notice and mail (``account_link``) to the linked account with a link to
the confirmation step. Confirmed or rejected: notice to the linking person.
Titles carry names only, never other personal data.
"""

from notifications.dispatch import common_context, queue_email
from notifications.inbox import notify, staff_with_permission
from notifications.models import InboxItem

from .account_links import CONFIRM_ROUTE, LINK_PERMISSION, describe
from .models import AccountLink


def staff_for(department_ids):
    """Account management of the record's departments (organisation scope without departments)."""
    if not department_ids:
        return set(staff_with_permission(LINK_PERMISSION, None))
    recipients = set()
    for department_id in department_ids:
        recipients |= set(staff_with_permission(LINK_PERMISSION, department_id))
    return recipients


def _name(user):
    return (user.get_full_name() or user.username) if user else "Die Kontoverwaltung"


def link_pending(link_id):
    from notifications.actions import make_link

    link = AccountLink.objects.select_related("user", "member", "parent", "linked_by").filter(pk=link_id).first()
    if link is None or link.status != AccountLink.Status.PENDING:
        return None
    user = link.user
    stamp = int(link.linked_at.timestamp()) if link.linked_at else 0
    item = notify(
        kind="account_link",
        category=InboxItem.Category.ACCOUNTS,
        title=f"Bitte bestätige die Verknüpfung mit {describe(link)}",
        obj=link,
        link=CONFIRM_ROUTE,
        recipients=[user],
        group_key=f"account_link:{link.pk}:{stamp}",
    )
    open_url = make_link(user, "open", {"r": CONFIRM_ROUTE})
    context = {
        **common_context(
            user,
            open_url=open_url,
            actions=[{"label": "Anmelden und bestätigen", "url": open_url, "style": "primary"}],
        ),
        "link": {"member_name": describe(link), "linked_by": _name(link.linked_by)},
    }
    queue_email("account_link", user, context, event_key=f"account_link:{link.pk}:{stamp}", explicit=True)
    return item


def link_decided(link_id):
    link = AccountLink.objects.select_related("user", "member", "parent", "linked_by").filter(pk=link_id).first()
    if link is None or link.linked_by_id is None or link.linked_by_id == link.user_id:
        return None
    confirmed = link.status == AccountLink.Status.CONFIRMED
    verb = "bestätigt" if confirmed else "abgelehnt – bitte prüfen"
    target = (
        f"/members/{link.member_id}"
        if link.member_id
        else f"/parents/{link.parent_id}/edit"
        if link.parent_id
        else "/users"
    )
    return notify(
        kind="account_link",
        category=InboxItem.Category.ACCOUNTS,
        title=f"{_name(link.user)} hat die Verknüpfung mit {describe(link)} {verb}",
        obj=link,
        link=target,
        recipients=[link.linked_by],
    )
