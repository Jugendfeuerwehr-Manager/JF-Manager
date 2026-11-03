"""Art. 15 DSGVO: a complete data copy per person, export right + audit. Fictional data."""

import io
import json
import zipfile
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import override_settings
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import ExportAudit, Member, Parent
from privacy.models import ConsentRecord
from qualifications.models import Qualification, QualificationType

User = get_user_model()
URL = "/api/v1/privacy/subject-access/"


def role(user, department, *codenames):
    group = Group.objects.create(name=f"{user.username}-{department.code}")
    group.permissions.add(*Permission.objects.filter(codename__in=codenames))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class SubjectAccessTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="sar-mitte")
        self.nord = Department.objects.create(name="Nord", code="sar-nord")
        self.member = Member.objects.create(
            name="Mia", lastname="Muster", birthday=date(2012, 5, 17), city="Musterstadt"
        )
        self.member.departments.add(self.mitte)
        self.parent = Parent.objects.create(name="Eva", lastname="Muster", email="eva@example.invalid")
        self.parent.children.add(self.member)
        Qualification.objects.create(
            member=self.member,
            type=QualificationType.objects.create(name="Leistungsspange"),
            date_acquired=date(2023, 6, 1),
        )
        ConsentRecord.objects.create(member=self.member, kind="photo_internal", status="granted", source="staff")
        self.exporter = User.objects.create_user("jugendwart", password="x")
        role(self.exporter, self.mitte, "view_member", "export_member", "view_parent")

    def archive(self, response):
        return zipfile.ZipFile(io.BytesIO(response.content))

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.get(f"{URL}?member={self.member.pk}").status_code, (401, 403))

    def test_read_right_without_export_right_is_refused(self):
        reader = User.objects.create_user("betreuer", password="x")
        role(reader, self.mitte, "view_member")
        self.client.force_authenticate(reader)
        self.assertEqual(self.client.get(f"{URL}?member={self.member.pk}").status_code, 403)
        self.assertFalse(ExportAudit.objects.exists())

    def test_foreign_department_cannot_reach_the_member(self):
        stranger = User.objects.create_user("nord", password="x")
        role(stranger, self.nord, "view_member", "export_member")
        self.client.force_authenticate(stranger)
        self.assertEqual(self.client.get(f"{URL}?member={self.member.pk}").status_code, 404)

    def test_member_archive_contains_all_sections_and_is_audited(self):
        self.client.force_authenticate(self.exporter)
        response = self.client.get(f"{URL}?member={self.member.pk}")
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        data = json.loads(self.archive(response).read("daten.json"))
        self.assertEqual(data["stammdaten"]["city"], "Musterstadt")
        self.assertEqual(data["eltern"][0]["email"], "eva@example.invalid")
        self.assertEqual(data["qualifikationen"][0]["type"]["bezeichnung"], "Leistungsspange")
        self.assertEqual(data["einwilligungen"][0]["kind"], "photo_internal")
        self.assertIn("LIESMICH.txt", self.archive(response).namelist())
        audit = ExportAudit.objects.get()
        self.assertEqual(
            (audit.action, audit.object_type, audit.object_id), ("subject_access", "members.member", self.member.pk)
        )

    def test_parent_archive(self):
        self.client.force_authenticate(self.exporter)
        response = self.client.get(f"{URL}?parent={self.parent.pk}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(self.archive(response).read("daten.json"))
        self.assertEqual(data["kinder"][0]["name"], "Mia Muster")

    def test_own_account_without_password_hash(self):
        self.client.force_authenticate(self.exporter)
        response = self.client.get(f"{URL}?user={self.exporter.pk}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(self.archive(response).read("daten.json"))
        self.assertNotIn("password", data["konto"])
        self.assertEqual(data["abteilungsrollen"][0]["abteilung"], "Mitte")

    # Session test about scope/step-up, not MFA (covered in privacy.tests.test_hardening).

    @override_settings(MFA_REQUIRED_FOR_MEMBER_DATA=False)
    def test_step_up_is_required_for_real_sessions(self):
        from users import mfa

        self.client.force_login(self.exporter)
        session = self.client.session
        session[mfa.REAUTH_KEY] = 0  # confirmation long ago
        session.save()
        response = self.client.get(f"{URL}?member={self.member.pk}")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "reauthentication_required")
