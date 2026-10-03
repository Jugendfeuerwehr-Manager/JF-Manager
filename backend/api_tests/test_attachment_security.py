import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.base import ContentFile
from django.test import override_settings
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, Member, Parent


class AttachmentSecurityTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Nord", code="north")
        self.foreign_department = Department.objects.create(name="Süd", code="south")
        self.user = get_user_model().objects.create_user(username="viewer", password="test-password-long")
        self.group = Group.objects.create(name="Members viewer")
        self.group.permissions.add(Permission.objects.get(codename="view_member"))
        role = UserDepartmentRole.objects.create(user=self.user, department=self.department)
        role.groups.add(self.group)
        self.member = Member.objects.create(name="Visible", lastname="Member")
        self.member.departments.add(self.department)
        foreign = Member.objects.create(name="Foreign", lastname="Member")
        foreign.departments.add(self.foreign_department)
        self.own_attachment = Attachment.objects.create(content_object=self.member, name="Own document")
        self.foreign_attachment = Attachment.objects.create(content_object=foreign, name="Private document")
        self.client.force_authenticate(self.user)

    def test_list_only_includes_authorized_owners(self):
        response = self.client.get("/api/v1/attachments/")
        self.assertEqual(response.status_code, 200)
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual([row["id"] for row in data], [self.own_attachment.pk])

    def test_foreign_attachment_is_inaccessible_for_all_actions(self):
        url = f"/api/v1/attachments/{self.foreign_attachment.pk}/"
        for response in (self.client.get(url), self.client.get(url + "download/"), self.client.patch(url, {"name": "Changed"}), self.client.delete(url)):
            self.assertEqual(response.status_code, 404)
        self.assertTrue(Attachment.objects.filter(pk=self.foreign_attachment.pk).exists())

    def test_view_permission_does_not_allow_attachment_modification(self):
        url = f"/api/v1/attachments/{self.own_attachment.pk}/"
        self.assertEqual(self.client.patch(url, {"name": "Changed"}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_owner_edit_permission_allows_modification(self):
        self.group.permissions.add(Permission.objects.get(codename="change_member"))
        response = self.client.patch(f"/api/v1/attachments/{self.own_attachment.pk}/", {"name": "Renamed"})
        self.assertEqual(response.status_code, 200)
        self.own_attachment.refresh_from_db()
        self.assertEqual(self.own_attachment.name, "Renamed")

    def test_generic_creation_is_disabled(self):
        response = self.client.post("/api/v1/attachments/", {"name": "Injection", "object_id": self.member.pk})
        self.assertEqual(response.status_code, 405)

    def test_unknown_owner_type_is_not_exposed(self):
        orphan = Attachment.objects.create(content_object=self.user, name="Not a supported owner")
        self.assertEqual(self.client.get(f"/api/v1/attachments/{orphan.pk}/").status_code, 404)

    def test_parent_write_requires_model_permission(self):
        parent = Parent.objects.create(name="Parent", lastname="Example")
        self.group.permissions.add(Permission.objects.get(codename="view_parent"))
        response = self.client.patch(f"/api/v1/parents/{parent.pk}/", {"name": "Changed"})
        self.assertEqual(response.status_code, 403)

    def test_parent_cannot_be_linked_to_foreign_child(self):
        self.group.permissions.add(Permission.objects.get(codename="add_parent"))
        foreign = Member.objects.exclude(pk=self.member.pk).get()
        response = self.client.post("/api/v1/parents/", {"name": "New", "lastname": "Parent", "children": [foreign.pk]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_member_upload_resolves_owner_on_server(self):
        self.group.permissions.add(Permission.objects.get(codename="change_member"))
        response = self.client.post(f"/api/v1/members/{self.member.pk}/attachments/", {
            "name": "Document", "object_id": self.foreign_attachment.object_id,
            "content_type": self.foreign_attachment.content_type_id,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Attachment.objects.get(pk=response.data["id"]).content_object, self.member)

    def test_member_upload_requires_edit_permission_and_scope(self):
        url = f"/api/v1/members/{self.member.pk}/attachments/"
        self.assertEqual(self.client.post(url, {"name": "Document"}).status_code, 403)
        self.group.permissions.add(Permission.objects.get(codename="change_member"))
        foreign_url = f"/api/v1/members/{self.foreign_attachment.object_id}/attachments/"
        self.assertEqual(self.client.post(foreign_url, {"name": "Document"}).status_code, 404)

    def test_attachment_preview_uses_short_signed_link_and_blocks_raw_path(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.own_attachment.file.save("example.pdf", ContentFile(b"fictitious document"))
            data = self.client.get(f"/api/v1/attachments/{self.own_attachment.pk}/").data
            self.assertIn("/api/v1/attachment-preview/", data["file_url"])
            self.assertEqual(data["file"], data["file_url"])
            self.assertNotIn("/uploads/", data["file_url"])
            self.assertEqual(self.client.get(self.own_attachment.file.url).status_code, 404)
            self.client.force_authenticate(None)
            response = self.client.get(data["file_url"])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"fictitious document")
            self.assertEqual(response["Cache-Control"], "private, no-store")
            forged = data["file_url"].replace(f"/{self.own_attachment.pk}/", f"/{self.foreign_attachment.pk}/")
            self.assertEqual(self.client.get(forged).status_code, 404)
