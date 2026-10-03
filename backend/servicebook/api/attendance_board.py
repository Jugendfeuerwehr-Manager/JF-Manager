"""Scoped attendance roster and compare-and-set updates for collaborative entry."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from members.models import Member
from servicebook.models import Attendance, Service, StaffAttendance

from .attendance_permissions import has_department_permission


class BoardChangeSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["member", "staff"])
    person_id = serializers.IntegerField(min_value=1)
    state = serializers.ChoiceField(choices=["A", "E", "F"], allow_null=True)
    expected_state = serializers.ChoiceField(choices=["A", "E", "F"], allow_null=True)


def roster_people(service):
    members = Member.objects.all()
    staff = get_user_model().objects.filter(is_active=True)
    if service.department_id:
        members = members.filter(departments=service.department_id)
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
    return Response(
        {
            "members": [
                {"id": p.pk, "full_name": p.get_full_name(), "state": member_states.get(p.pk)} for p in members
            ],
            "staff": [
                {"id": p.pk, "full_name": p.get_full_name() or p.username, "state": staff_states.get(p.pk)}
                for p in staff
            ],
        }
    )


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
    with transaction.atomic():
        # Lock the parent even when no attendance exists yet; serializes concurrent inserts.
        Service.objects.select_for_update().get(pk=service.pk)
        records = model.objects.filter(service=service, person_id=change["person_id"])
        current = records.values_list("state", flat=True).first()
        if current != change["expected_state"]:
            return Response(
                {
                    "detail": "Diese Anwesenheit wurde inzwischen geändert. Bitte den aktuellen Stand prüfen.",
                    "state": current,
                },
                status=409,
            )
        if change["state"] is None:
            records.delete()
        else:
            model.objects.update_or_create(
                service=service, person_id=change["person_id"], defaults={"state": change["state"]}
            )
    cache.delete("attendance_over_time_data")
    return Response({"state": change["state"]})


def staff_report(services):
    result = {}
    for attendance in (
        StaffAttendance.objects.filter(service__in=services)
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
