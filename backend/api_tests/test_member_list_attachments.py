from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from members.models import MemberList


class MemberListAttachmentsApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            username="list_attachment_user",
            email="list_attachment_user@example.com",
            password="pw12345",
        )

        self.member_list = MemberList.objects.create(
            name="Ausflug 2026",
            description="Packliste",
            color="#10B981",
        )

        self.view_perm = Permission.objects.get(codename="view_memberlist")
        self.add_perm = Permission.objects.get(codename="add_memberlist")
        self.change_perm = Permission.objects.get(codename="change_memberlist")
        self.delete_perm = Permission.objects.get(codename="delete_memberlist")

    def test_attachments_require_authentication(self):
        response = self.client.get(f"/api/v1/member-lists/{self.member_list.id}/attachments/")
        self.assertIn(response.status_code, [401, 403])

    def test_upload_requires_change_permission(self):
        self.user.user_permissions.add(self.view_perm, self.add_perm)
        self.client.force_authenticate(user=self.user)

        upload = SimpleUploadedFile("liste.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        response = self.client.post(
            f"/api/v1/member-lists/{self.member_list.id}/attachments/",
            {
                "name": "Teilnehmerliste",
                "file": upload,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)

    def test_list_upload_delete_attachment(self):
        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm)
        self.client.force_authenticate(user=self.user)

        upload = SimpleUploadedFile("teilnehmerliste.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\n", content_type="application/pdf")

        create_response = self.client.post(
            f"/api/v1/member-lists/{self.member_list.id}/attachments/",
            {
                "name": "Teilnehmerliste",
                "description": "Stand vor Abfahrt",
                "file": upload,
            },
            format="multipart",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["name"], "Teilnehmerliste")
        attachment_id = create_response.data["id"]

        list_response = self.client.get(f"/api/v1/member-lists/{self.member_list.id}/attachments/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["id"], attachment_id)

        delete_response = self.client.delete(f"/api/v1/member-lists/{self.member_list.id}/attachments/{attachment_id}/")
        self.assertEqual(delete_response.status_code, 204)

        list_after_delete = self.client.get(f"/api/v1/member-lists/{self.member_list.id}/attachments/")
        self.assertEqual(list_after_delete.status_code, 200)
        self.assertEqual(list_after_delete.data, [])
