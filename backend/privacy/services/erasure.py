"""Anonymize or erase a member without leaving personal traces (Art. 17 DSGVO).

Anonymizing keeps the row for statistics and the service book: gender, joined,
left_at, birth year, departments, group, status, attendance and
qualifications stay. Everything that identifies the person goes, including
copies in other tables (e-mail recipients, change log, inbox titles, sync
bindings, inventory names).
"""

from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

ANONYMOUS_FIRST_NAME = "Ehemaliges"


class ErasureError(Exception):
    pass


def anonymous_lastname(member):
    return f"Mitglied #{member.pk}"


def _release_storage_locations(member, keep_name=False):
    """Unlink personal storage locations; their names would identify the member."""
    from django.db.models import Q

    from inventory.models import Stock, StorageLocation, Transaction

    locations = list(StorageLocation.objects.select_for_update().filter(member=member))
    location_ids = [location.pk for location in locations]
    if member.storage_location_id:
        location_ids.append(member.storage_location_id)
    if Stock.objects.filter(location_id__in=location_ids, quantity__gt=0).exists():
        raise ErasureError(
            "Vor dem Löschen oder Anonymisieren müssen alle Bestände des Mitglieds zurückgebucht werden."
        )
    for location in locations:
        location.member = None
        location.is_member = False
        if not keep_name:
            location.name = f"Ehemaliges Mitglied #{location.pk}"
        location.save(update_fields=["member", "is_member", "name"])
    if not keep_name and location_ids:
        Transaction.objects.filter(
            Q(source_id__in=location_ids) | Q(target_id__in=location_ids)
        ).clear_former_member_names()


def _scrub_traces(member):
    """Personal copies outside the member row."""
    from external_sync.models import SyncBinding
    from members.models import EmailMessage, EmailRecipient
    from notifications.models import InboxItem
    from portal.models import ChangeLog

    EmailRecipient.objects.filter(member=member).update(
        member=None,
        email_address="geloescht@invalid.invalid",
        recipient_name="Gelöscht",
        personalized_body_html="",
        personalized_body_text="",
    )
    EmailMessage.objects.filter(recipient_member=member).update(recipient_member=None)
    ChangeLog.objects.filter(target_kind="member", target_id=member.pk).delete()
    InboxItem.objects.filter(object_type="members.member", object_id=member.pk).update(
        title=f"Ehemaliges Mitglied #{member.pk}"
    )
    SyncBinding.objects.filter(content_type=ContentType.objects.get_for_model(member), object_id=member.pk).delete()


def _release_parents(member):
    """Parents kept only for this child go as well; others just lose the link."""
    for parent in list(member.parent_set.all()):
        parent.children.remove(member)
        if not parent.children.exists():
            from portal.models import ChangeLog

            ChangeLog.objects.filter(target_kind="parent", target_id=parent.pk).delete()
            parent.delete()


@transaction.atomic
def anonymize_member(member, *, by=None):
    from members.models import Event, Member, MemberListEntry
    from orders.models import Order
    from participation.models import Registration
    from qualifications.models import Qualification, SpecialTask

    member = Member.objects.select_for_update().get(pk=member.pk)
    if member.anonymized_at:
        raise ErasureError("Dieses Mitglied ist bereits anonymisiert.")
    _release_storage_locations(member)
    _scrub_traces(member)
    _release_parents(member)
    for attachment in member.attachments.all():
        attachment.delete()  # one by one, so django_cleanup removes the files
    Event.objects.filter(member=member).delete()
    MemberListEntry.objects.filter(member=member).update(notes="")
    Registration.objects.filter(member=member).update(reason_note="", reason_category="")
    Qualification.objects.filter(member=member).update(note="")
    SpecialTask.objects.filter(member=member).update(note="")
    Order.objects.filter(member=member).update(notes="")
    member.consent_records.all().delete()
    if member.avatar:
        member.avatar.delete(save=False)
    member.name = ANONYMOUS_FIRST_NAME
    member.lastname = anonymous_lastname(member)
    for field in (
        "email",
        "street",
        "zip_code",
        "city",
        "phone",
        "mobile",
        "notes",
        "identityCardNumber",
        "health_notes",
    ):
        setattr(member, field, "")
    member.canSwimm = False
    member.storage_location = None
    if member.birthday:
        member.birthday = date(member.birthday.year, 1, 1)
    member.left_at = member.left_at or timezone.localdate()
    member.anonymized_at = timezone.now()
    member.save()
    from notifications import inbox

    inbox.complete_tasks(member, kind="privacy_anonymize_due", by=by)
    return member


@transaction.atomic
def erase_member(member, *, keep_inventory_name=False):
    """Delete the member and every personal trace; ``keep_inventory_name`` keeps the
    name of former personal storage locations in the booking history."""
    from members.models import Member

    member = Member.objects.select_for_update().get(pk=member.pk)
    _release_storage_locations(member, keep_name=keep_inventory_name)
    _scrub_traces(member)
    _release_parents(member)
    member.delete()


def members_due_for_anonymization(days, today=None):
    from members.models import Member

    today = today or timezone.localdate()
    return Member.objects.filter(
        anonymized_at__isnull=True, left_at__isnull=False, left_at__lte=today - timezone.timedelta(days=days)
    )
