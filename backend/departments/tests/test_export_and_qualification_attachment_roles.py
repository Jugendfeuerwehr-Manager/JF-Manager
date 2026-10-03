"""Exports and qualification attachments follow scoped model rights."""

from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent
from qualifications.models import Qualification, QualificationType


class ExportAndQualificationAttachmentRoleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="A", code="export-qualification-a")
        cls.member = Member.objects.create(name="A", lastname="Member")
        cls.member.departments.add(cls.department)
        qualification_type = QualificationType.objects.create(name="Course")
        cls.qualification = Qualification.objects.create(
            member=cls.member, type=qualification_type, date_acquired=date(2026, 1, 1)
        )
        cls.user = get_user_model().objects.create_user(username="qualified-viewer", password="test-only-password")
        group = Group.objects.create(name="Scoped member and qualification editor")
        group.permissions.add(
            Permission.objects.get(content_type__app_label="members", codename="view_member"),
            Permission.objects.get(content_type__app_label="qualifications", codename="view_qualification"),
            Permission.objects.get(content_type__app_label="qualifications", codename="add_qualification"),
            Permission.objects.get(content_type__app_label="qualifications", codename="change_qualification"),
        )
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department).groups.add(group)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_scoped_member_view_right_allows_scoped_export(self):
        response = self.client.get("/api/v1/members/export-excel/?columns=name")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_does_not_include_parents_without_parent_view_right(self):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="members", codename="view_member"))
        parent = Parent.objects.create(name="Parent", lastname="Example", email="private-parent@example.invalid")
        parent.children.add(self.member)

        response = self.client.get("/api/v1/members/export-excel/?columns=name,parent1_email")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sheet = load_workbook(BytesIO(response.content), read_only=True).active
        self.assertEqual(sheet.cell(row=2, column=2).value, None)

    def test_scoped_qualification_edit_right_allows_attachment_upload(self):
        upload = SimpleUploadedFile("course.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        response = self.client.post(
            f"/api/v1/qualifications/{self.qualification.pk}/attachments/",
            {"file": upload, "name": "Course document"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.qualification.attachments.count(), 1)
