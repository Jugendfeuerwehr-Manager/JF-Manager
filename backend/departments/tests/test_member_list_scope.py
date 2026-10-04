"""SEC-03: list and attachment access must follow the list's department."""

from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, Member, MemberList, MemberListEntry


class MemberListDepartmentScopeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="List A", code="list-scope-a")
        cls.department_b = Department.objects.create(name="List B", code="list-scope-b")
        cls.member_a = Member.objects.create(name="A", lastname="List member")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b = Member.objects.create(name="B", lastname="List member")
        cls.member_b.departments.add(cls.department_b)

        # Before SEC-03.2, MemberList has no department field. Keep the same
        # HTTP regression fixtures usable once the model gains that field.
        has_department = any(field.name == "department" for field in MemberList._meta.fields)
        cls.list_a = MemberList.objects.create(
            name="List A", **({"department": cls.department_a} if has_department else {})
        )
        cls.list_b = MemberList.objects.create(
            name="List B", **({"department": cls.department_b} if has_department else {})
        )
        cls.entry_a = MemberListEntry.objects.create(member_list=cls.list_a, member=cls.member_a)
        cls.entry_b = MemberListEntry.objects.create(
            member_list=cls.list_b, member=cls.member_b, notes="Private B note"
        )
        cls.attachment_a = Attachment.objects.create(content_object=cls.list_a, name="A list attachment")
        cls.attachment_b = Attachment.objects.create(content_object=cls.list_b, name="B list attachment")

        cls.editor_a = get_user_model().objects.create_user(username="list-editor-a", password="test-only-password")
        role_group = Group.objects.create(name="List editor A")
        role_group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="members",
                codename__in=["view_memberlist", "add_memberlist", "change_memberlist", "delete_memberlist"],
            )
        )
        UserDepartmentRole.objects.create(user=cls.editor_a, department=cls.department_a).groups.add(role_group)
        # The export and nested attachment actions currently check global
        # permissions directly. Grant them to isolate the owner scope decision.
        cls.editor_a.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="members", codename__in=["view_memberlist", "change_memberlist"]
            )
        )

    def setUp(self):
        self.client.force_authenticate(user=self.editor_a)

    def _url(self, member_list):
        return f"/api/v1/member-lists/{member_list.pk}/"

    def test_list_and_department_filter_exclude_foreign_list(self):
        for params in ({}, {"department": self.department_a.pk}):
            with self.subTest(params=params):
                response = self.client.get("/api/v1/member-lists/", params)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                ids = {item["id"] for item in response.data["results"]}
                self.assertIn(self.list_a.pk, ids)
                self.assertNotIn(self.list_b.pk, ids)

    def test_foreign_detail_does_not_reveal_entries(self):
        response = self.client.get(self._url(self.list_b))

        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.assertNotIn("Private B note", str(response.data))

    def test_foreign_list_cannot_be_renamed(self):
        response = self.client.patch(self._url(self.list_b), {"name": "Changed"}, format="json")

        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.list_b.refresh_from_db()
        self.assertEqual(self.list_b.name, "List B")

    def test_foreign_export_is_denied(self):
        response = self.client.get(f"{self._url(self.list_b)}export-excel/")

        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_permitted_department_can_export_its_list(self):
        response = self.client.get(f"{self._url(self.list_a)}export-excel/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_foreign_nested_attachments_are_hidden(self):
        response = self.client.get(f"{self._url(self.list_b)}attachments/")

        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_generic_attachment_list_and_detail_hide_foreign_list_attachment(self):
        response = self.client.get("/api/v1/attachments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data["results"]}
        self.assertIn(self.attachment_a.pk, ids)
        self.assertNotIn(self.attachment_b.pk, ids)

        detail = self.client.get(f"/api/v1/attachments/{self.attachment_b.pk}/")
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_foreign_list_attachment_download_is_denied(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.attachment_b.file.save("b-list.pdf", SimpleUploadedFile("b-list.pdf", b"%PDF-1.4\n"), save=True)
            response = self.client.get(f"/api/v1/attachments/{self.attachment_b.pk}/download/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_foreign_list_attachment_cannot_be_changed_or_deleted(self):
        changed = self.client.patch(f"/api/v1/attachments/{self.attachment_b.pk}/", {"name": "Changed"}, format="json")
        deleted = self.client.delete(f"/api/v1/attachments/{self.attachment_b.pk}/")

        self.assertEqual(changed.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(deleted.status_code, status.HTTP_404_NOT_FOUND)
        self.attachment_b.refresh_from_db()
        self.assertEqual(self.attachment_b.name, "B list attachment")

    def test_foreign_list_entries_cannot_be_checked_or_edited(self):
        operations = [
            ("post", "toggle_check/", {"member_id": self.member_b.pk}),
            ("post", "set_check/", {"member_id": self.member_b.pk, "checked": True}),
            ("post", "check_all/", {}),
            ("patch", "update_entry_notes/", {"member_id": self.member_b.pk, "notes": "Changed"}),
        ]
        for method, action, payload in operations:
            with self.subTest(action=action):
                response = getattr(self.client, method)(f"{self._url(self.list_b)}{action}", payload, format="json")
                self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.entry_b.refresh_from_db()
        self.assertFalse(self.entry_b.checked)
        self.assertEqual(self.entry_b.notes, "Private B note")

    def test_mixed_add_member_target_is_rejected_without_partial_write(self):
        response = self.client.post(
            f"{self._url(self.list_a)}bulk_add/",
            {"member_ids": [self.member_a.pk, self.member_b.pk]},
            format="json",
        )

        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.assertEqual(set(self.list_a.entries.values_list("member_id", flat=True)), {self.member_a.pk})

    def test_single_foreign_member_target_is_rejected(self):
        response = self.client.post(
            f"{self._url(self.list_a)}add_member/", {"member_id": self.member_b.pk}, format="json"
        )

        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )
        self.assertFalse(self.list_a.entries.filter(member=self.member_b).exists())

    def test_permitted_department_can_read_and_update_its_list(self):
        listing = self.client.get("/api/v1/member-lists/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertIn(self.list_a.pk, {item["id"] for item in listing.data["results"]})

        changed = self.client.post(
            f"{self._url(self.list_a)}set_check/",
            {"member_id": self.member_a.pk, "checked": True},
            format="json",
        )
        self.assertEqual(changed.status_code, status.HTTP_200_OK)
        self.entry_a.refresh_from_db()
        self.assertTrue(self.entry_a.checked)
