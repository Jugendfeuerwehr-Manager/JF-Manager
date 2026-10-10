"""Scoped attendance roster and compare-and-set updates for collaborative entry."""

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from members.models import Member
from servicebook.models import Attendance, Service, StaffAttendance
from users.people import ANONYMOUS_USERNAME, person_accounts

from ..linked_people import CountedAsOther, check_single_entry, members_for_staff, staff_for_members
from .attendance_permissions import has_department_permission


class BoardChangeSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["member", "staff"])
    person_id = serializers.IntegerField(min_value=1)
    state = serializers.ChoiceField(choices=["A", "E", "F"], allow_null=True)
    expected_state = serializers.ChoiceField(choices=["A", "E", "F"], allow_null=True)
    # PORTAL-04.4: move a linked person's entry from the other list instead of refusing.
    replace_linked = serializers.BooleanField(required=False, default=False)


def roster_people(service):
    members = Member.objects.all()
    staff = person_accounts()
    if service.department_id:
        # Guests (registered or assigned from outside the department) and anyone already recorded stay listed.
        guests = Q(attendance__service=service)
        if service.training_session_id:
            guests |= Q(
                registrations__session_id=service.training_session_id,
                registrations__state__in=["registered", "assigned"],
            )
        members = members.filter(Q(departments=service.department_id) | guests)
        staff = staff.filter(
            Q(department_roles__department_id=service.department_id) | Q(service_attendances__service=service)
        )
    return members.distinct().order_by("lastname", "name"), staff.distinct().order_by(
        "last_name", "first_name", "username"
    )


def board_response(service):
    members, staff = roster_people(service)
    member_states = dict(Attendance.objects.filter(service=service).values_list("person_id", "state"))
    staff_states = dict(StaffAttendance.objects.filter(service=service).values_list("person_id", "state"))
    members, staff = list(members), list(staff)
    # Same person in both lists (confirmed staff/member link): each row names its counterpart.
    member_links = staff_for_members([p.pk for p in members])
    staff_links = members_for_staff([p.pk for p in staff])
    return Response(
        {
            "members": [
                {
                    "id": p.pk,
                    "full_name": p.get_full_name(),
                    "state": member_states.get(p.pk),
                    "linked_staff_id": member_links.get(p.pk),
                }
                for p in members
            ],
            "staff": [
                {
                    "id": p.pk,
                    "full_name": p.get_full_name() or p.username,
                    "state": staff_states.get(p.pk),
                    "linked_member_id": staff_links.get(p.pk),
                }
                for p in staff
            ],
        }
    )


def set_attendance(service, model, person_id, state, expected_state, replace_linked=False):
    """Compare-and-set one attendance value; returns ``(applied, current_state)``. The only write path.

    Raises ``CountedAsOther`` when a linked person already has an entry in the other list
    (PORTAL-04.4); ``replace_linked`` moves that entry here instead.
    """
    with transaction.atomic():
        # Lock the parent even when no attendance exists yet; serializes concurrent inserts.
        Service.objects.select_for_update().get(pk=service.pk)
        records = model.objects.filter(service=service, person_id=person_id)
        current = records.values_list("state", flat=True).first()
        if current != expected_state:
            return False, current
        if state is not None:
            check_single_entry(service, model, person_id, replace=replace_linked)
        if state is None:
            records.delete()
        else:
            model.objects.update_or_create(service=service, person_id=person_id, defaults={"state": state})
    cache.delete("attendance_over_time_data")
    return True, state


def update_board(request, service):
    if not has_department_permission(request.user, "servicebook.change_attendance", service.department_id):
        raise PermissionDenied("Keine Berechtigung zum Bearbeiten der Anwesenheit.")
    serializer = BoardChangeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    change = serializer.validated_data
    members, staff = roster_people(service)
    people = members if change["kind"] == "member" else staff
    if not people.filter(pk=change["person_id"]).exists():
        raise serializers.ValidationError({"person_id": "Person gehört nicht zur Teilnehmerliste dieses Dienstes."})
    model = Attendance if change["kind"] == "member" else StaffAttendance
    try:
        applied, current = set_attendance(
            service,
            model,
            change["person_id"],
            change["state"],
            change["expected_state"],
            replace_linked=change["replace_linked"],
        )
    except CountedAsOther as error:
        return Response({"detail": str(error), "code": "counted_as_other", "recorded_as": error.kind}, status=409)
    if not applied:
        return Response(
            {
                "detail": "Diese Anwesenheit wurde inzwischen geändert. Bitte den aktuellen Stand prüfen.",
                "state": current,
            },
            status=409,
        )
    return Response({"state": change["state"]})


def staff_report(services):
    result = {}
    for attendance in (
        StaffAttendance.objects.filter(service__in=services)
        .exclude(person__username=ANONYMOUS_USERNAME)
        .select_related("person", "service")
        .order_by("person__last_name", "person__first_name")
    ):
        person = attendance.person
        row = result.setdefault(
            person.pk,
            {
                "id": person.pk,
                "full_name": person.get_full_name() or person.username,
                "present": 0,
                "excused": 0,
                "absent": 0,
                "total": 0,
                "hours": 0,
            },
        )
        row[{"A": "present", "E": "excused", "F": "absent"}[attendance.state]] += 1
        row["total"] += 1
        if attendance.state == "A":
            row["hours"] += max(0, (attendance.service.end - attendance.service.start).total_seconds() / 3600)
    for row in result.values():
        row["hours"] = round(row["hours"], 2)
    return Response({"results": list(result.values())})
