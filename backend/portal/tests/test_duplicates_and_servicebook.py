"""PORTAL-04.4: qualification duplicates and "participant or staff" in the service book."""

from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, Member
from portal.models import AccountLink
from qualifications.models import Qualification, QualificationType
from servicebook.attendance_report import attendance_report
from servicebook.models import Attendance, Service, StaffAttendance

User = get_user_model()
URL = "/api/v1/portal/account-links/"


def role(user, department, *rights):
    group = AuthGroup.objects.create(name=f"Rolle {user.username}")
    for right in rights:
        app, codename = right.split(".")
        group.permissions.add(Permission.objects.get(codename=codename, content_type__app_label=app))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class DuplicateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.nord = Department.objects.create(name="Nord")
        cls.leader = User.objects.create_user("leitung", first_name="Tobias", last_name="Lehmann")
        cls.manager = User.objects.create_user("qualis")
        role(
            cls.manager,
            cls.mitte,
            "qualifications.view_qualification",
            "qualifications.change_qualification",
            "qualifications.delete_qualification",
        )
        cls.reader = User.objects.create_user("leser")
        role(cls.reader, cls.mitte, "qualifications.view_qualification")
        cls.outsider = User.objects.create_user("nord")
        role(
            cls.outsider,
            cls.nord,
            "qualifications.view_qualification",
            "qualifications.change_qualification",
            "qualifications.delete_qualification",
        )
        cls.member = Member.objects.create(name="Tobias", lastname="Lehmann")
        cls.member.departments.add(cls.mitte)
        cls.first_aid = QualificationType.objects.create(name="Erste Hilfe")
        cls.juleica = QualificationType.objects.create(name="Juleica")
        cls.driver = QualificationType.objects.create(name="Fahrer")

    def setUp(self):
        self.link = AccountLink.objects.create(user=self.leader, member=self.member, status="confirmed")
        day = date(2025, 3, 1)
        self.member_aid = Qualification.objects.create(type=self.first_aid, member=self.member, date_acquired=day)
        self.account_aid = Qualification.objects.create(
            type=self.first_aid, user=self.leader, date_acquired=day, date_expires=date(2027, 3, 1)
        )
        Qualification.objects.create(type=self.juleica, member=self.member, date_acquired=date(2020, 1, 1))
        self.account_juleica = Qualification.objects.create(
            type=self.juleica, user=self.leader, date_acquired=date(2024, 1, 1)
        )
        self.account_driver = Qualification.objects.create(type=self.driver, user=self.leader, date_acquired=day)

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_duplicates_list_pairs_of_the_same_type(self):
        data = self.client_for(self.manager).get(f"{URL}duplicates/", {"member": self.member.pk}).data
        self.assertEqual(data["link"], self.link.pk)
        self.assertEqual(
            [(r["type"], r["same_date"]) for r in data["results"]], [("Erste Hilfe", True), ("Juleica", False)]
        )

    def test_merge_keeps_the_evidence_at_the_member(self):
        content_type = ContentType.objects.get_for_model(Qualification)
        Attachment.objects.create(
            content_type=content_type,
            object_id=self.account_aid.pk,
            name="Nachweis",
            file=ContentFile(b"Nachweis", "n.txt"),
        )
        response = self.client_for(self.manager).post(
            f"{URL}merge-qualifications/",
            {"member": self.member.pk, "qualifications": [self.account_aid.pk, self.account_juleica.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["merged"], 2)
        self.assertEqual(response.data["results"], [])
        self.assertFalse(Qualification.objects.filter(pk=self.account_aid.pk).exists())
        self.member_aid.refresh_from_db()
        self.assertEqual(self.member_aid.date_expires, date(2027, 3, 1))
        self.assertEqual(self.member_aid.attachments.count(), 1)
        self.account_juleica.refresh_from_db()
        self.assertEqual((self.account_juleica.member_id, self.account_juleica.user_id), (self.member.pk, None))
        # Types without a counterpart stay at the account.
        self.assertEqual(Qualification.objects.get(pk=self.account_driver.pk).user, self.leader)

    def test_merge_refuses_types_without_duplicate_and_foreign_records(self):
        client = self.client_for(self.manager)
        body = {"member": self.member.pk, "qualifications": [self.account_driver.pk]}
        self.assertEqual(client.post(f"{URL}merge-qualifications/", body, format="json").data["code"], "no_duplicate")
        foreign = Qualification.objects.create(type=self.first_aid, member=self.member, date_acquired=date(2021, 1, 1))
        body = {"member": self.member.pk, "qualifications": [foreign.pk]}
        self.assertEqual(client.post(f"{URL}merge-qualifications/", body, format="json").status_code, 404)

    def test_rights(self):
        self.assertEqual(
            self.client_for(self.reader).get(f"{URL}duplicates/", {"member": self.member.pk}).status_code, 403
        )
        self.assertEqual(
            self.client_for(self.outsider).get(f"{URL}duplicates/", {"member": self.member.pk}).status_code, 404
        )
        # The linked person never merges their own evidence.
        role(
            self.leader,
            self.mitte,
            "qualifications.view_qualification",
            "qualifications.change_qualification",
            "qualifications.delete_qualification",
        )
        response = self.client_for(self.leader).post(
            f"{URL}merge-qualifications/",
            {"member": self.member.pk, "qualifications": [self.account_aid.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "own_record")

    def test_pending_link_has_no_duplicates(self):
        AccountLink.objects.filter(pk=self.link.pk).update(status="pending")
        data = self.client_for(self.manager).get(f"{URL}duplicates/", {"member": self.member.pk}).data
        self.assertEqual((data["link"], data["results"]), (None, []))


class ParticipantOrStaffTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.admin = User.objects.create_superuser("admin")
        cls.leader = User.objects.create_user("leitung", first_name="Tobias", last_name="Lehmann")
        UserDepartmentRole.objects.create(user=cls.leader, department=cls.mitte)
        cls.member = Member.objects.create(name="Tobias", lastname="Lehmann")
        cls.member.departments.add(cls.mitte)
        AccountLink.objects.create(user=cls.leader, member=cls.member, status="confirmed")
        start = timezone.make_aware(datetime(2026, 9, 1, 18))
        cls.service = Service.objects.create(
            start=start, end=start + timedelta(hours=2), topic="Übung", department=cls.mitte
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.url = f"/api/v1/servicebook/services/{self.service.pk}/attendance_board/"

    def board_change(self, kind, person_id, state, expected=None, **extra):
        return self.client.patch(
            self.url,
            {"kind": kind, "person_id": person_id, "state": state, "expected_state": expected, **extra},
            format="json",
        )

    def test_board_names_the_counterpart(self):
        data = self.client.get(self.url).data
        member_row = next(r for r in data["members"] if r["id"] == self.member.pk)
        staff_row = next(r for r in data["staff"] if r["id"] == self.leader.pk)
        self.assertEqual(member_row["linked_staff_id"], self.leader.pk)
        self.assertEqual(staff_row["linked_member_id"], self.member.pk)

    def test_person_is_participant_or_staff_never_both(self):
        self.assertEqual(self.board_change("staff", self.leader.pk, "A").status_code, 200)
        response = self.board_change("member", self.member.pk, "A")
        self.assertEqual(response.status_code, 409)
        self.assertEqual((response.data["code"], response.data["recorded_as"]), ("counted_as_other", "staff"))
        self.assertFalse(Attendance.objects.exists())
        response = self.board_change("member", self.member.pk, "A", replace_linked=True)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(StaffAttendance.objects.exists())
        self.assertEqual(Attendance.objects.get().state, "A")

    def test_classic_attendance_api_refuses_the_second_entry(self):
        StaffAttendance.objects.create(person=self.leader, service=self.service, state="A")
        response = self.client.post(
            "/api/v1/servicebook/attendances/bulk_update/",
            {"service": self.service.pk, "attendances": [{"person_id": self.member.pk, "state": "A"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Attendance.objects.exists())

    def test_evaluation_counts_the_person_once(self):
        Attendance.objects.create(person=self.member, service=self.service, state="A")
        StaffAttendance.objects.create(person=self.leader, service=self.service, state="A")  # legacy double entry
        report = attendance_report(Service.objects.all(), date(2026, 8, 1), date(2026, 9, 30))
        self.assertEqual(report["members"]["summary"]["people"], 1)
        self.assertEqual(report["staff"]["summary"]["people"], 0)
