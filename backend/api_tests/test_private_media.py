import io
import tempfile
from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, EmailAttachment, EmailMessage, Member
from training.models import LibraryBlock, TrainingBlock, TrainingMedia, TrainingSession


def image_file():
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, "PNG")
    return SimpleUploadedFile("avatar.png", buffer.getvalue(), content_type="image/png")


class PrivateMediaTests(APITestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        settings = override_settings(MEDIA_ROOT=root.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = get_user_model().objects.create_user(username="media-reader")
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=["view_member", "view_trainingsession", "view_trainingblock"]))
        self.department = Department.objects.create(name="A", code="media-a")
        self.foreign = Department.objects.create(name="B", code="media-b")
        UserDepartmentRole.objects.create(user=self.user, department=self.department)
        self.member = Member.objects.create(name="Synthetic", lastname="Image", avatar=image_file())
        self.member.departments.add(self.department)
        session = TrainingSession.objects.create(title="Private training", status="published", date=date(2030, 1, 1), start_time=time(18), end_time=time(20), department=self.department)
        self.block = TrainingBlock.objects.create(session=session, title="Image", duration_minutes=10)
        self.media = TrainingMedia.objects.create(content_object=self.block, file=image_file())
        self.client.force_authenticate(self.user)

    def test_member_and_training_files_recheck_department_and_deny_anonymous(self):
        urls = [f"/api/v1/private-media/member-avatar/{self.member.pk}/", f"/api/v1/private-media/training/{self.media.pk}/"]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "private, no-store")
            b"".join(response.streaming_content)  # closes the file without request_finished
        self.member.departments.set([self.foreign])
        self.block.session.department = self.foreign
        self.block.session.save()
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(None)
        for url in urls:
            self.assertIn(self.client.get(url).status_code, (401, 403))

    def test_user_avatar_survives_subsequent_save_and_has_private_url(self):
        self.user.avatar = image_file()
        self.user.save()
        self.user.save(update_fields=["first_name"])
        response = self.client.get("/api/v1/users/me/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/private-media/user-avatar/", response.data["avatar"])
        self.assertNotIn("/uploads/", response.data["avatar_url"])

    def test_shared_library_media_still_requires_login(self):
        library = LibraryBlock.objects.create(title="Shared")
        media = TrainingMedia.objects.create(content_object=library, file=image_file())
        response = self.client.get(f"/api/v1/private-media/training/{media.pk}/")
        self.assertEqual(response.status_code, 200)
        b"".join(response.streaming_content)  # closes the file without request_finished

    def test_email_attachment_is_scoped_to_its_sender(self):
        self.user.user_permissions.add(Permission.objects.get(codename="can_send_member_emails"))
        message = EmailMessage.objects.create(sender=self.user, subject="Synthetic", department=self.department, body_html="", recipient_type="all")
        attachment = EmailAttachment.objects.create(email_message=message, file=SimpleUploadedFile("test.txt", b"test"), original_filename="test.txt")
        url = f"/api/v1/private-media/email-attachment/{attachment.pk}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        b"".join(response.streaming_content)  # closes the file without request_finished
        message.sender = get_user_model().objects.create_user(username="other-sender")
        message.save()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_forged_upload_and_owner_limit_leave_no_attachment(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_member"))
        url = f"/api/v1/members/{self.member.pk}/attachments/"
        bad = SimpleUploadedFile("bad.png", b"<script>bad()</script>", content_type="image/png")
        self.assertEqual(self.client.post(url, {"name": "Bad", "file": bad}).status_code, 400)
        self.assertEqual(Attachment.objects.count(), 0)
        for index in range(20):
            Attachment.objects.create(content_object=self.member, name=str(index), file=SimpleUploadedFile(f"{index}.txt", b"test"))
        response = self.client.post(url, {"name": "Overflow", "file": SimpleUploadedFile("limit.txt", b"test")})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attachment.objects.count(), 20)
