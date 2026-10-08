import io
import shutil
import tempfile
from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, Group
from training.models import LibraryBlock, TrainingBlock, TrainingMedia, TrainingSession, TrainingTemplate

MEDIA = tempfile.mkdtemp(prefix="train-template-media-")


def png(name="bild.png"):
    stream = io.BytesIO()
    Image.new("RGB", (4, 4), "blue").save(stream, "PNG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")


def read(field):
    with field.open("rb") as stream:
        return stream.read()


@override_settings(MEDIA_ROOT=MEDIA)
class TemplateAndCopyTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="template-test")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.department = Department.objects.create(name="Vorlagen", code="templates")
        self.group = Group.objects.create(name="Gruppe A", department=self.department)
        self.session = TrainingSession.objects.create(
            title="Knotenabend",
            description="Grundlagen",
            date=date(2099, 3, 1),
            start_time=time(18),
            end_time=time(20),
            location="Gerätehaus",
            department=self.department,
            status="published",
        )
        self.session.groups.set([self.group])
        self.block = TrainingBlock.objects.create(session=self.session, title="Mastwurf", duration_minutes=30)
        self.block.groups.set([self.group])
        block_type = ContentType.objects.get_for_model(TrainingBlock)
        self.media = TrainingMedia.objects.create(content_type=block_type, object_id=self.block.pk, file=png())
        self.block.content = f'<p><img src="https://jf.example{self.media.url}"></p>'
        self.block.save()
        self.attachment = Attachment.objects.create(
            content_type=block_type,
            object_id=self.block.pk,
            name="Knotentafel",
            file=SimpleUploadedFile("tafel.pdf", b"%PDF-1.4 knoten", content_type="application/pdf"),
        )

    def delete_source_files(self):
        self.media.file.delete()
        self.media.delete()
        self.attachment.file.delete()
        self.attachment.delete()

    def assert_independent_block(self, block):
        copy = TrainingMedia.objects.get(content_type=ContentType.objects.get_for_model(block), object_id=block.pk)
        attachment = Attachment.objects.get(content_type=ContentType.objects.get_for_model(block), object_id=block.pk)
        self.assertIn(f'src="https://jf.example{copy.url}"', block.content)
        self.assertTrue(read(copy.file).startswith(b"\x89PNG"))
        self.assertEqual(read(attachment.file), b"%PDF-1.4 knoten")
        self.assertEqual(attachment.name, "Knotentafel")

    def test_save_as_template_and_instantiate_survive_source_deletion(self):
        response = self.client.post(
            f"/api/v1/training/sessions/{self.session.pk}/save_as_template/", {"title": "Knoten-Vorlage"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        template = TrainingTemplate.objects.get(pk=response.data["id"])
        self.assertEqual(
            (template.title, template.location, template.department_id),
            ("Knoten-Vorlage", "Gerätehaus", self.department.pk),
        )
        self.assert_independent_block(template.blocks.get())

        self.delete_source_files()
        self.session.delete()

        detail = self.client.get(f"/api/v1/training/templates/{template.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["blocks"][0]["title"], "Mastwurf")
        created = self.client.post(
            f"/api/v1/training/templates/{template.pk}/instantiate/", {"date": "2099-04-01"}, format="json"
        )
        self.assertEqual(created.status_code, 201, created.data)
        session = TrainingSession.objects.get(pk=created.data["id"])
        self.assertEqual((session.status, session.date, session.title), ("draft", date(2099, 4, 1), "Knoten-Vorlage"))
        self.assertIsNone(session.series_uuid)
        self.assertEqual(list(session.groups.all()), [self.group])
        block = session.blocks.get()
        self.assertEqual(list(block.groups.all()), [self.group])
        self.assert_independent_block(block)

        # Deleting the template keeps the exercise and its own files intact.
        self.assertEqual(self.client.delete(f"/api/v1/training/templates/{template.pk}/").status_code, 204)
        block.refresh_from_db()
        self.assert_independent_block(block)

    def test_groups_moved_to_other_department_are_not_carried_over(self):
        response = self.client.post(f"/api/v1/training/sessions/{self.session.pk}/save_as_template/", {}, format="json")
        other = Department.objects.create(name="Andere", code="other-template")
        Group.objects.filter(pk=self.group.pk).update(department=other)
        created = self.client.post(
            f"/api/v1/training/templates/{response.data['id']}/instantiate/", {"date": "2099-04-01"}, format="json"
        )
        session = TrainingSession.objects.get(pk=created.data["id"])
        self.assertFalse(session.groups.exists())
        self.assertFalse(session.blocks.get().groups.exists())

    def test_copy_creates_independent_draft(self):
        response = self.client.post(
            f"/api/v1/training/sessions/{self.session.pk}/copy/", {"date": "2099-05-01"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        copy = TrainingSession.objects.get(pk=response.data["id"])
        self.assertEqual((copy.status, copy.title, copy.revision), ("draft", "Knotenabend", 1))
        self.assertIsNone(copy.series_parent_id)
        self.assertEqual(response.data["linked_service_id"], None)
        self.delete_source_files()
        self.assert_independent_block(copy.blocks.get())
        self.block.title = "Später geändert"
        self.block.save()
        self.assertEqual(copy.blocks.get().title, "Mastwurf")

    def test_template_access_is_limited_to_planners_of_the_department(self):
        template = self.client.post(
            f"/api/v1/training/sessions/{self.session.pk}/save_as_template/", {}, format="json"
        ).data
        reader = get_user_model().objects.create_user(username="template-reader")
        reader.user_permissions.add(Permission.objects.get(codename="view_trainingsession"))
        UserDepartmentRole.objects.create(user=reader, department=self.department)
        self.client.force_authenticate(reader)
        self.assertEqual(self.client.get("/api/v1/training/templates/").status_code, 403)
        self.assertEqual(
            self.client.post(
                f"/api/v1/training/templates/{template['id']}/instantiate/", {"date": "2099-04-01"}
            ).status_code,
            403,
        )
        media = TrainingMedia.objects.filter(content_type__model="trainingtemplateblock").get()
        self.assertEqual(self.client.get(media.url).status_code, 404)
        # Template attachments are read-only even for planners.
        self.client.force_authenticate(self.user)
        attachment = Attachment.objects.get(content_type__model="trainingtemplateblock")
        self.assertEqual(self.client.get(f"/api/v1/attachments/{attachment.pk}/download/").status_code, 200)
        self.assertEqual(self.client.get(media.url).status_code, 200)

    def test_only_name_and_description_are_editable(self):
        template = self.client.post(
            f"/api/v1/training/sessions/{self.session.pk}/save_as_template/", {}, format="json"
        ).data
        response = self.client.patch(
            f"/api/v1/training/templates/{template['id']}/",
            {"title": "Neu", "description": "Beschreibung", "location": "Woanders"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["title"], response.data["location"]), ("Neu", "Gerätehaus"))


@override_settings(MEDIA_ROOT=MEDIA)
class LibraryAdoptionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="library-adoption")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.library = LibraryBlock.objects.create(title="Leinen", content="<p>Grundlage</p>", color="#ff0000")
        library_type = ContentType.objects.get_for_model(LibraryBlock)
        self.used = TrainingMedia.objects.create(content_type=library_type, object_id=self.library.pk, file=png())
        self.unused = TrainingMedia.objects.create(
            content_type=library_type, object_id=self.library.pk, file=png("x.png")
        )
        self.library.content = f'<p><img src="https://jf.example{self.used.url}"></p>'
        self.library.save()
        Attachment.objects.create(
            content_type=library_type,
            object_id=self.library.pk,
            name="Merkblatt",
            file=SimpleUploadedFile("merk.pdf", b"%PDF-1.4 merk", content_type="application/pdf"),
        )
        self.session = TrainingSession.objects.create(
            title="Übung", date=date(2099, 3, 1), start_time=time(18), end_time=time(20)
        )

    def test_plan_adoption_copies_library_files_and_ignores_later_library_changes(self):
        response = self.client.put(
            f"/api/v1/training/sessions/{self.session.pk}/plan/",
            {
                "expected_revision": 1,
                "session": {"title": "Übung", "date": "2099-03-01", "start_time": "18:00", "end_time": "20:00"},
                "blocks": [
                    {
                        "title": "Leinen",
                        "library_block": self.library.pk,
                        "content": self.library.content,
                        "duration_minutes": 30,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        block = self.session.blocks.get()
        block_type = ContentType.objects.get_for_model(TrainingBlock)
        copies = TrainingMedia.objects.filter(content_type=block_type, object_id=block.pk)
        self.assertEqual(copies.count(), 1, "only referenced images are copied")
        self.assertIn(copies.get().url, block.content)
        self.assertEqual(Attachment.objects.filter(content_type=block_type, object_id=block.pk).get().name, "Merkblatt")
        # Library edits and deletions do not reach the planned block.
        self.library.content = "<p>Neu</p>"
        self.library.save()
        self.used.file.delete()
        self.used.delete()
        block.refresh_from_db()
        self.assertNotIn("Neu", block.content)
        self.assertTrue(read(copies.get().file).startswith(b"\x89PNG"))
