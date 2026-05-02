from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department
from training.models import TrainingBlock, TrainingSession


class TrainingBlockAttachmentUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="training_attachment_admin",
            email="training_attachment_admin@example.com",
            password="pw12345",
        )
        self.client.force_authenticate(user=self.user)

        self.department = Department.objects.create(name="Abteilung West", code="west")
        self.session = TrainingSession.objects.create(
            title="Funkubung",
            description="",
            date=date(2030, 4, 10),
            start_time=time(18, 0),
            end_time=time(20, 0),
            department=self.department,
            created_by=self.user,
        )
        self.block = TrainingBlock.objects.create(
            title="Lagekarte",
            session=self.session,
            duration_minutes=30,
        )

    def test_upload_attachment_without_generic_fk_fields(self):
        upload = SimpleUploadedFile(
            "checkliste.pdf",
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n",
            content_type="application/pdf",
        )

        response = self.client.post(
            f"/api/v1/training/blocks/{self.block.id}/attachments/",
            {
                "name": "Checkliste",
                "file": upload,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Checkliste")
        self.assertEqual(response.data["mime_type"], "application/pdf")
