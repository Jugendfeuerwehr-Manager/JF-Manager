"""Delete or blank personal data after its retention period (Art. 5 Abs. 1 e DSGVO)."""

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from dynamic_preferences.registries import global_preferences_registry

from privacy.retention_settings import RETENTIONS


@dataclass
class PurgeResult:
    name: str
    label: str
    cutoff: object
    count: int


def retention_days(name):
    default = next(retention.default for retention in RETENTIONS if retention.name == name)
    value = global_preferences_registry.manager().get(f"privacy__{name}")
    return value if isinstance(value, int) and value > 0 else default


def _cutoff(name):
    return timezone.now() - timedelta(days=retention_days(name))


def _email_history(cutoff, dry_run):
    from members.models import EmailMessage

    # Delete row by row so attachment files go too (django_cleanup); never touch a send in progress.
    queryset = EmailMessage.objects.filter(created_at__lt=cutoff).exclude(status="sending")
    if dry_run:
        return queryset.count()
    count = 0
    for message in queryset.iterator():
        message.delete()
        count += 1
    return count


def _notification_log(cutoff, dry_run):
    from orders.models import NotificationLog

    queryset = NotificationLog.objects.filter(created_at__lt=cutoff)
    return queryset.count() if dry_run else queryset.delete()[0]


def _email_outbox(cutoff, dry_run):
    from notifications.models import EmailDelivery

    queryset = EmailDelivery.objects.filter(created_at__lt=cutoff)
    return queryset.count() if dry_run else queryset.delete()[0]


def _push_outbox(cutoff, dry_run):
    from notifications.models import PushDelivery

    queryset = PushDelivery.objects.filter(created_at__lt=cutoff)
    return queryset.count() if dry_run else queryset.delete()[0]


def _sync_runs(cutoff, dry_run):
    from external_sync.models import SyncRun

    queryset = SyncRun.objects.filter(created_at__lt=cutoff).exclude(status__in=["pending", "running"])
    return queryset.count() if dry_run else queryset.delete()[0]


def _portal_changelog(cutoff, dry_run):
    from portal.models import ChangeLog

    queryset = ChangeLog.objects.filter(applied_at__lt=cutoff)
    return queryset.count() if dry_run else queryset.delete()[0]


def _absence_illness(cutoff, dry_run):
    from participation.models import Registration

    queryset = Registration.objects.filter(
        reason_category=Registration.Reason.ILLNESS, session__date__lt=timezone.localtime(cutoff).date()
    )
    return queryset.count() if dry_run else queryset.update(reason_category="")


NOTICE_DAYS = 30


def _former_members(cutoff, dry_run):
    """Anonymize members whose leave date passed the period; announce it 30 days ahead."""
    from privacy.services.erasure import anonymize_member, members_due_for_anonymization

    days = retention_days("member_anonymize_after_days")
    due = list(members_due_for_anonymization(days))
    if dry_run:
        return len(due)
    _announce(members_due_for_anonymization(days - NOTICE_DAYS).exclude(pk__in=[m.pk for m in due]), days)
    for member in due:
        anonymize_member(member)
    return len(due)


def _announce(members, days):
    from notifications import inbox
    from notifications.models import InboxItem

    for member in members.prefetch_related("departments"):
        if InboxItem.objects.filter(
            kind="privacy_anonymize_due", object_type="members.member", object_id=member.pk
        ).exists():
            continue
        when = member.left_at + timedelta(days=days)
        department = member.departments.first()
        inbox.notify(
            kind="privacy_anonymize_due",
            category=InboxItem.Category.ACCOUNTS,
            item_type=InboxItem.ItemType.TASK,
            title=f"{member.name} {member.lastname} wird am {when:%d.%m.%Y} anonymisiert",
            department=department,
            obj=member,
            permission="members.anonymize_member",
            link=f"/members/{member.pk}",
        )


PURGES = {
    "member_anonymize_after_days": _former_members,
    "email_history_days": _email_history,
    "notification_log_days": _notification_log,
    "email_outbox_days": _email_outbox,
    "push_outbox_days": _push_outbox,
    "sync_run_days": _sync_runs,
    "portal_changelog_days": _portal_changelog,
    "absence_illness_days": _absence_illness,
}


def purge_personal_data(dry_run=False):
    results = []
    for retention in RETENTIONS:
        cutoff = _cutoff(retention.name)
        with transaction.atomic():
            count = PURGES[retention.name](cutoff, dry_run)
        results.append(PurgeResult(retention.name, retention.label, cutoff, count))
    return results
