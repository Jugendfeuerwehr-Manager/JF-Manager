"""Qualification duplicates of a confirmed staff link (PORTAL-04.4, concept 4.10, E10).

Once an account is confirmed as a member, the same qualification type may be
recorded twice: at the account (``Qualification.user``) and at the member.
Staff with the qualification rights in the member's department see these
pairs and merge them; nothing is merged automatically. The evidence stays at
the member: an account record of the same day moves its attachments to the
member record and is deleted; any other account record is moved to the
member (it then counts as earlier or later evidence of the same type).
The linked person never merges their own records (four-eyes).
"""

import logging

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from members.models import Attachment
from qualifications.models import Qualification

from .invitations import departments_with_permission, record_department_ids
from .models import AccountLink
from .self_records import deny_own_evidence

security_log = logging.getLogger("security.portal")
MERGE_PERMISSIONS = ("qualifications.change_qualification", "qualifications.delete_qualification")


class MergeError(Exception):
    def __init__(self, code, detail, status=400):
        super().__init__(detail)
        self.code, self.detail, self.status = code, detail, status


def link_for_member(member):
    return (
        AccountLink.objects.select_related("user", "member")
        .filter(member=member, status=AccountLink.Status.CONFIRMED, user__account_kind="staff")
        .first()
    )


def may_merge(user, member):
    departments = record_department_ids(member)
    for permission in MERGE_PERMISSIONS:
        allowed = departments_with_permission(user, permission)
        if allowed is not None and not (allowed & departments):
            return False
    return True


def _row(qualification):
    return {
        "id": qualification.pk,
        "acquired": qualification.date_acquired.isoformat() if qualification.date_acquired else None,
        "expires": qualification.date_expires.isoformat() if qualification.date_expires else None,
        "attachments": qualification.attachments.count(),
    }


def duplicates(link):
    """Pairs of the same type at account and member: one entry per account qualification."""
    if link is None or link.member_id is None:
        return []
    member_rows = {}
    for q in Qualification.objects.filter(member_id=link.member_id).order_by("-date_acquired"):
        member_rows.setdefault(q.type_id, q)
    rows = []
    for q in Qualification.objects.filter(user_id=link.user_id).select_related("type").order_by("type__name"):
        twin = member_rows.get(q.type_id)
        if twin is None:
            continue
        rows.append(
            {
                "type": q.type.name,
                "account": _row(q),
                "member": _row(twin),
                "same_date": q.date_acquired == twin.date_acquired,
            }
        )
    return rows


@transaction.atomic
def merge(actor, link, qualification_ids):
    """Merge the chosen account qualifications into the member; returns the number merged."""
    deny_own_evidence(actor, member_id=link.member_id, person_user_id=link.user_id)
    wanted = {pk for pk in qualification_ids if isinstance(pk, int)}
    if not wanted:
        raise MergeError("nothing_selected", "Bitte mindestens eine Qualifikation wählen.")
    member_types = {}
    for q in Qualification.objects.select_for_update().filter(member_id=link.member_id):
        member_types.setdefault(q.type_id, []).append(q)
    account_rows = list(Qualification.objects.select_for_update().filter(user_id=link.user_id, pk__in=wanted))
    if len(account_rows) != len(wanted):
        raise MergeError("unknown", "Mindestens eine Qualifikation gehört nicht zu diesem Konto.", 404)
    content_type = ContentType.objects.get_for_model(Qualification)
    merged = 0
    for q in account_rows:
        twins = member_types.get(q.type_id)
        if not twins:
            raise MergeError("no_duplicate", f"„{q.type.name}“ ist am Mitglied nicht erfasst.")
        same_day = next((t for t in twins if t.date_acquired == q.date_acquired), None)
        if same_day is not None:
            Attachment.objects.filter(content_type=content_type, object_id=q.pk).update(object_id=same_day.pk)
            if same_day.date_expires is None and q.date_expires is not None:
                same_day.date_expires = q.date_expires
                same_day.save(update_fields=["date_expires"])
            q.delete()
        else:
            q.user = None
            q.member_id = link.member_id
            q.save(update_fields=["user", "member"])
        merged += 1
    security_log.info("qualifications merged", extra={"link": link.pk, "actor": actor.pk, "count": merged})
    return merged
