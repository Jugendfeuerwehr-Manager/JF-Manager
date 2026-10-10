"""One person, one entry per service (PORTAL-04.4, concept 4.10).

A staff account confirmed as linked to a member record is the same person: per
service it is recorded either as participant (``Attendance``) or as staff
(``StaffAttendance``), never both. Evaluations count such a person once.
"""

from portal.models import AccountLink

from .models import Attendance, StaffAttendance


class CountedAsOther(Exception):
    """The linked counterpart already has an entry for this service."""

    def __init__(self, kind):
        self.kind = kind  # kind of the existing entry: "member" or "staff"
        label = "Betreuer/in" if kind == "staff" else "Teilnehmende/r"
        super().__init__(f"Diese Person ist für diesen Dienst bereits als {label} erfasst.")


def _links():
    return AccountLink.objects.filter(
        status=AccountLink.Status.CONFIRMED, member__isnull=False, user__account_kind="staff"
    )


def staff_for_members(member_ids):
    """{member_id: user_id} of confirmed links."""
    return dict(_links().filter(member_id__in=member_ids).values_list("member_id", "user_id"))


def members_for_staff(user_ids):
    """{user_id: member_id} of confirmed links."""
    return dict(_links().filter(user_id__in=user_ids).values_list("user_id", "member_id"))


def counterpart(model, person_id):
    """(other model, other person id) or (None, None) without a confirmed link."""
    if model is Attendance:
        other = staff_for_members([person_id]).get(person_id)
        return (StaffAttendance, other) if other else (None, None)
    other = members_for_staff([person_id]).get(person_id)
    return (Attendance, other) if other else (None, None)


def check_single_entry(service, model, person_id, *, replace=False):
    """Raise ``CountedAsOther`` when the counterpart is recorded; with ``replace`` remove that entry."""
    other_model, other_id = counterpart(model, person_id)
    if other_model is None:
        return
    entries = other_model.objects.filter(service=service, person_id=other_id)
    if not entries.exists():
        return
    if replace:
        entries.delete()
        return
    raise CountedAsOther("staff" if other_model is StaffAttendance else "member")


def drop_double_staff_rows(member_rows, staff_rows):
    """Staff rows of linked people who are already counted as participants of the same service."""
    links = members_for_staff({row[0] for row in staff_rows})
    if not links:
        return staff_rows
    recorded = {(person_id, service_id) for person_id, service_id, _state in member_rows}
    return [row for row in staff_rows if (links.get(row[0]), row[1]) not in recorded]
