from django.test import TestCase

from departments.models import Department
from members.api_serializers import EventSerializer, MemberCreateUpdateSerializer
from members.models import EventType, Group, Member


class MemberDepartmentGroupConsistencyTests(TestCase):
    def setUp(self):
        self.department_a = Department.objects.create(name="Abteilung A", code="abt-a")
        self.department_b = Department.objects.create(name="Abteilung B", code="abt-b")
        self.group_a = Group.objects.create(name="Gruppe A", department=self.department_a)

    def test_rejects_group_outside_member_departments_when_group_explicitly_set(self):
        member = Member.objects.create(name="Max", lastname="Mustermann")
        member.departments.set([self.department_b])

        serializer = MemberCreateUpdateSerializer(
            instance=member,
            data={"group": self.group_a.id, "departments": [self.department_b.id]},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("group", serializer.errors)

    def test_clears_existing_group_when_departments_change_to_another_org(self):
        member = Member.objects.create(name="Eva", lastname="Muster", group=self.group_a)
        member.departments.set([self.department_a])

        serializer = MemberCreateUpdateSerializer(
            instance=member,
            data={"departments": [self.department_b.id]},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_member = serializer.save()

        self.assertIsNone(updated_member.group)
        self.assertSetEqual(set(updated_member.departments.values_list("id", flat=True)), {self.department_b.id})


class MemberEventTypeDepartmentConsistencyTests(TestCase):
    def setUp(self):
        self.department_a = Department.objects.create(name="Abteilung Event A", code="evt-a")
        self.department_b = Department.objects.create(name="Abteilung Event B", code="evt-b")
        self.member = Member.objects.create(name="Lena", lastname="Beispiel")
        self.member.departments.set([self.department_b])
        self.event_type_a = EventType.objects.create(name="Wechsel", department=self.department_a)
        self.event_type_global = EventType.objects.create(name="Geburtstag", department=None)

    def test_rejects_department_mismatch_between_member_and_event_type(self):
        serializer = EventSerializer(
            data={
                "member": self.member.id,
                "type": self.event_type_a.id,
                "datetime": "2026-05-02",
                "notes": "Test",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)

    def test_allows_global_event_type_for_any_member_department(self):
        serializer = EventSerializer(
            data={
                "member": self.member.id,
                "type": self.event_type_global.id,
                "datetime": "2026-05-02",
                "notes": "Test",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
