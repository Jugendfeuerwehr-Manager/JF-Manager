"""Inbox for staff and portal notices (NOTIF-01.1, concept 4.9.2, E15).

Producers call ``notify`` with a short title (no free text from requests or
cancellation notes), a department, the permission that makes an entry
relevant, and optionally explicit recipients (D10: responsible staff of a
service). Notices with a ``group_key`` are bundled: a new event raises the
count, moves the entry up and marks it unread again. Tasks carry a team status
and are completed automatically once their subject is done.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from .models import InboxItem, InboxRecipient

User = get_user_model()


def staff_with_permission(permission, department_id):
    """Active staff accounts holding ``permission`` in ``department_id`` (D9).

    Either a department role grants it there, or the global right plus an
    assignment to the department (or organisation-wide scope). Superusers are
    not addressed implicitly; they would receive every team entry.
    """
    app_label, codename = permission.split(".", 1)
    grants = {
        "groups__permissions__content_type__app_label": app_label,
        "groups__permissions__codename": codename,
    }
    direct = Q(user_permissions__content_type__app_label=app_label, user_permissions__codename=codename)
    global_right = direct | Q(**grants)
    org_wide = Q(
        user_permissions__codename="can_access_all_departments",
        user_permissions__content_type__app_label="departments",
    ) | Q(
        groups__permissions__codename="can_access_all_departments",
        groups__permissions__content_type__app_label="departments",
    )
    staff = User.objects.filter(is_active=True, account_kind=User.AccountKind.STAFF)
    if department_id is None:
        return staff.filter(global_right & org_wide).distinct()
    role = Q(
        department_roles__department_id=department_id,
        department_roles__groups__permissions__content_type__app_label=app_label,
        department_roles__groups__permissions__codename=codename,
    )
    assigned = Q(department_roles__department_id=department_id)
    ids = set(staff.filter(role).values_list("pk", flat=True))
    ids |= set(staff.filter(global_right).filter(assigned | org_wide).values_list("pk", flat=True))
    return User.objects.filter(pk__in=ids)


def may_see(user, item):
    """Re-check at read time; withdrawn rights hide team entries (4.9.2)."""
    if not user.is_active:
        return False
    if not item.permission:
        return True  # personal notices (portal) carry no team right
    if user.is_superuser:
        return True
    from portal.invitations import departments_with_permission

    allowed = departments_with_permission(user, item.permission)
    if allowed is None:
        return True
    # Organisation-wide entries (no department) need organisation-wide scope.
    return item.department_id is not None and item.department_id in allowed


@transaction.atomic
def notify(
    *,
    kind,
    category,
    title,
    item_type=InboxItem.ItemType.NOTICE,
    department=None,
    obj=None,
    permission="",
    link="",
    recipients=None,
    group_key=None,
):
    """Create or bundle an inbox entry; returns the item or None without recipients."""
    department_id = getattr(department, "pk", department)
    if recipients is None:
        recipients = staff_with_permission(permission, department_id) if permission else User.objects.none()
    user_ids = {getattr(u, "pk", u) for u in recipients}
    if not user_ids:
        return None
    object_type, object_id = ("", None)
    if obj is not None:
        object_type, object_id = f"{obj._meta.app_label}.{obj._meta.model_name}", obj.pk
    now = timezone.now()
    item = None
    if group_key and item_type == InboxItem.ItemType.NOTICE:
        item = InboxItem.objects.select_for_update().filter(group_key=group_key).first()
    if item is not None:
        InboxItem.objects.filter(pk=item.pk).update(count=F("count") + 1, title=title, updated_at=now)
        item.refresh_from_db()
        InboxRecipient.objects.filter(item=item).update(read_at=None, hidden_at=None)
    else:
        values = dict(
            kind=kind,
            category=category,
            item_type=item_type,
            department_id=department_id,
            object_type=object_type,
            object_id=object_id,
            title=title[:200],
            link=link,
            permission=permission,
            group_key=group_key if item_type == InboxItem.ItemType.NOTICE else None,
            task_state=InboxItem.TaskState.OPEN if item_type == InboxItem.ItemType.TASK else "",
            updated_at=now,
        )
        try:
            with transaction.atomic():
                item = InboxItem.objects.create(**values)
        except IntegrityError:  # a parallel event created the bundle first
            item = InboxItem.objects.select_for_update().get(group_key=group_key)
            InboxItem.objects.filter(pk=item.pk).update(count=F("count") + 1, title=title, updated_at=now)
            item.refresh_from_db()
    existing = set(InboxRecipient.objects.filter(item=item).values_list("user_id", flat=True))
    InboxRecipient.objects.bulk_create([InboxRecipient(item=item, user_id=uid) for uid in user_ids - existing])
    return item


def complete_tasks(obj=None, *, object_type=None, object_id=None, kind=None, by=None, via="auto"):
    """Mark open tasks about an object as done (team status), e.g. once a request is decided."""
    if obj is not None:
        object_type, object_id = f"{obj._meta.app_label}.{obj._meta.model_name}", obj.pk
    tasks = InboxItem.objects.filter(
        item_type=InboxItem.ItemType.TASK,
        task_state=InboxItem.TaskState.OPEN,
        object_type=object_type,
        object_id=object_id,
    )
    if kind:
        tasks = tasks.filter(kind=kind)
    return tasks.update(task_state=InboxItem.TaskState.DONE, done_by=by, done_at=timezone.now(), done_via=via)


def entries_for(user):
    """Recipient rows of ``user`` that are not hidden, with items; visibility re-checked by the caller."""
    return (
        InboxRecipient.objects.filter(user=user, hidden_at__isnull=True)
        .select_related("item", "item__done_by", "item__department")
        .order_by("-item__updated_at", "-item__pk")
    )


def purge(now=None, days=180):
    """Delete done tasks and read notices after the retention period (4.9.2)."""
    cutoff = (now or timezone.now()) - timedelta(days=days)
    done = InboxItem.objects.filter(
        item_type=InboxItem.ItemType.TASK, task_state=InboxItem.TaskState.DONE, done_at__lt=cutoff
    )
    stale_notices = InboxItem.objects.filter(item_type=InboxItem.ItemType.NOTICE, updated_at__lt=cutoff).exclude(
        recipients__read_at__isnull=True
    )
    count = done.count() + stale_notices.count()
    done.delete()
    stale_notices.delete()
    return count
