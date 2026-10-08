"""SEC-03: list and attachment access must follow the list's department."""

from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
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
        role_group.permissions.add(Permission.objects.get(codename="export_memberlist"))
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

    def test_view_right_without_export_right_cannot_export_own_list(self):
        group = Group.objects.get(name="List editor A")
        group.permissions.remove(Permission.objects.get(codename="export_memberlist"))

        response = self.client.get(f"{self._url(self.list_a)}export-excel/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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

    def test_signed_preview_of_foreign_list_attachment_is_denied(self):
        from members.attachment_links import preview_url

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.attachment_b.file.save("b-list.pdf", SimpleUploadedFile("b-list.pdf", b"%PDF-1.4\n"), save=True)
            url = preview_url(self.attachment_b)
            self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
            self.client.force_authenticate(user=None)
            self.assertIn(
                self.client.get(url).status_code,
                (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
            )

    def test_unassigned_legacy_list_is_hidden_from_non_superusers(self):
        legacy = MemberList.objects.create(name="Legacy unresolved")
        legacy_attachment = Attachment.objects.create(content_object=legacy, name="Legacy attachment")
        self.editor_a.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))

        listing = self.client.get("/api/v1/member-lists/")
        detail = self.client.get(self._url(legacy))
        attachment = self.client.get(f"/api/v1/attachments/{legacy_attachment.pk}/")

        self.assertNotIn(legacy.pk, {item["id"] for item in listing.data["results"]})
        self.assertIn(self.list_b.pk, {item["id"] for item in listing.data["results"]})
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(attachment.status_code, status.HTTP_404_NOT_FOUND)

        superuser = get_user_model().objects.create_superuser(
            username="list-migration-admin", password="test-only-password"
        )
        self.client.force_authenticate(user=superuser)
        self.assertEqual(self.client.get(self._url(legacy)).status_code, status.HTTP_200_OK)

    def test_owned_list_with_foreign_legacy_entry_is_hidden_until_repaired(self):
        MemberListEntry.objects.create(member_list=self.list_a, member=self.member_b, notes="Foreign legacy data")

        listing = self.client.get("/api/v1/member-lists/")
        detail = self.client.get(self._url(self.list_a))
        exported = self.client.get(f"{self._url(self.list_a)}export-excel/")
        attachment = self.client.get(f"/api/v1/attachments/{self.attachment_a.pk}/")

        self.assertNotIn(self.list_a.pk, {item["id"] for item in listing.data["results"]})
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(exported.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(attachment.status_code, status.HTTP_404_NOT_FOUND)

    def test_shared_member_is_valid_in_a_list(self):
        self.member_b.departments.add(self.department_a)
        MemberListEntry.objects.create(member_list=self.list_a, member=self.member_b)

        listing = self.client.get("/api/v1/member-lists/")
        detail = self.client.get(self._url(self.list_a))

        self.assertIn(self.list_a.pk, {item["id"] for item in listing.data["results"]})
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["member"]["id"] for item in detail.data["entries"]},
            {self.member_a.pk, self.member_b.pk},
        )

    def test_legacy_list_preview_requires_superuser_and_orphan_preview_is_hidden(self):
        from members.attachment_links import preview_url

        legacy = MemberList.objects.create(name="Legacy preview")
        legacy_attachment = Attachment.objects.create(content_object=legacy, name="Legacy preview attachment")
        orphan = Attachment.objects.create(
            content_type=ContentType.objects.get_for_model(MemberList),
            object_id=999999,
            name="Orphan preview attachment",
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            legacy_attachment.file.save("legacy.pdf", SimpleUploadedFile("legacy.pdf", b"legacy"), save=True)
            orphan.file.save("orphan.pdf", SimpleUploadedFile("orphan.pdf", b"orphan"), save=True)
            legacy_url = preview_url(legacy_attachment)
            orphan_url = preview_url(orphan)

            self.assertEqual(self.client.get(legacy_url).status_code, status.HTTP_404_NOT_FOUND)
            superuser = get_user_model().objects.create_superuser(
                username="list-preview-admin", password="test-only-password"
            )
            self.client.force_authenticate(user=superuser)
            preview = self.client.get(legacy_url)
            self.assertEqual(preview.status_code, status.HTTP_200_OK)
            self.assertEqual(b"".join(preview.streaming_content), b"legacy")
            self.assertEqual(self.client.get(orphan_url).status_code, status.HTTP_404_NOT_FOUND)

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

    def test_change_role_without_add_role_can_edit_and_upload_own_list(self):
        group = Group.objects.get(name="List editor A")
        group.permissions.remove(Permission.objects.get(codename="add_memberlist"))
        self.editor_a.user_permissions.remove(Permission.objects.get(codename="change_memberlist"))
        self.client.force_authenticate(user=get_user_model().objects.get(pk=self.editor_a.pk))

        created = self.client.post(
            "/api/v1/member-lists/", {"name": "Not allowed", "department": self.department_a.pk}, format="json"
        )
        checked = self.client.post(
            f"{self._url(self.list_a)}set_check/",
            {"member_id": self.member_a.pk, "checked": True},
            format="json",
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            uploaded = self.client.post(
                f"{self._url(self.list_a)}attachments/",
                {"file": SimpleUploadedFile("a.pdf", b"%PDF-1.4\n")},
                format="multipart",
            )

        self.assertEqual(created.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(checked.status_code, status.HTTP_200_OK)
        self.assertEqual(uploaded.status_code, status.HTTP_201_CREATED)

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
