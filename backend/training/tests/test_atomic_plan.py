from datetime import date, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, Group
from training.models import TrainingBlock, TrainingMedia, TrainingSession


class AtomicPlanTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="atomic-plan")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.department = Department.objects.create(name="Plan A", code="plan-a")
        self.other_department = Department.objects.create(name="Plan B", code="plan-b")
        self.group = Group.objects.create(name="Gruppe A", department=self.department)
        self.foreign_group = Group.objects.create(name="Gruppe B", department=self.other_department)
        self.session = TrainingSession.objects.create(
            title="Plan",
            date=date(2030, 1, 1),
            start_time=time(18),
            end_time=time(20),
            department=self.department,
        )
        self.block = TrainingBlock.objects.create(session=self.session, title="Bestand", duration_minutes=30)
        self.url = f"/api/v1/training/sessions/{self.session.pk}/plan/"
        self.metadata = {
            "title": "Neuer Plan",
            "date": "2030-01-02",
            "start_time": "18:00:00",
            "end_time": "20:00:00",
            "department": self.department.pk,
            "group_ids": [self.group.pk],
        }

    def payload(self, blocks=None, revision=1):
        return {
            "expected_revision": revision,
            "session": self.metadata,
            "blocks": blocks
            if blocks is not None
            else [
                {
                    "id": self.block.pk,
                    "title": "Bearbeitet",
                    "duration_minutes": 30,
                    "start_offset_minutes": 30,
                    "group_ids": [self.group.pk],
                },
            ],
        }

    def save(self, data):
        return self.client.put(self.url, data, format="json")

    def assert_unchanged(self):
        self.session.refresh_from_db()
        self.block.refresh_from_db()
        self.assertEqual(self.session.title, "Plan")
        self.assertEqual(self.session.revision, 1)
        self.assertEqual(self.block.title, "Bestand")
        self.assertEqual(self.block.start_offset_minutes, 0)

    def test_saves_metadata_blocks_and_groups_once_and_preserves_media_identity(self):
        ct = ContentType.objects.get_for_model(self.block)
        media = TrainingMedia.objects.create(content_type=ct, object_id=self.block.pk, file="training/existing.jpg")
        attachment = Attachment.objects.create(content_type=ct, object_id=self.block.pk, name="Testdatei")
        response = self.save(self.payload())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["revision"], 2)
        self.assertEqual(response.data["blocks"][0]["id"], self.block.pk)
        self.assertEqual(response.data["blocks"][0]["title"], "Bearbeitet")
        self.assertEqual(response.data["blocks"][0]["groups"][0]["id"], self.group.pk)
        self.assertTrue(TrainingMedia.objects.filter(pk=media.pk, object_id=self.block.pk).exists())
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk, object_id=self.block.pk).exists())
        self.assertEqual(self.session.servicebook_entry.topic, "Neuer Plan")

    def test_invalid_second_block_changes_nothing(self):
        data = self.payload()
        data["blocks"].append({"title": "Ungültig", "duration_minutes": 0})
        response = self.save(data)
        self.assertEqual(response.status_code, 400)
        self.assert_unchanged()
        self.assertEqual(self.session.blocks.count(), 1)

    def test_database_error_after_first_block_rolls_back_all_changes(self):
        from training.api.serializers.block import TrainingBlockCreateSerializer

        original = TrainingBlockCreateSerializer.save
        calls = []

        def fail_second(serializer, **kwargs):
            calls.append(serializer)
            if len(calls) == 2:
                raise RuntimeError("synthetic write failure")
            return original(serializer, **kwargs)

        data = self.payload()
        data["blocks"].append({"title": "Neu", "duration_minutes": 15})
        with patch.object(TrainingBlockCreateSerializer, "save", fail_second), self.assertRaises(RuntimeError):
            self.save(data)
        self.assert_unchanged()
        self.assertEqual(self.session.blocks.count(), 1)

    def test_stale_plan_returns_current_version_without_writing(self):
        self.assertEqual(self.save(self.payload()).status_code, 200)
        data = self.payload()
        data["session"]["title"] = "Veralteter Entwurf"
        response = self.save(data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "plan_revision_conflict")
        self.assertEqual(response.data["current"]["revision"], 2)
        self.assertEqual(response.data["current"]["title"], "Neuer Plan")
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 2)

    def test_revision_is_required_and_cannot_be_written_in_metadata(self):
        data = self.payload()
        del data["expected_revision"]
        self.assertEqual(self.save(data).status_code, 400)
        data = self.payload()
        data["session"]["revision"] = 100
        self.assertEqual(self.save(data).data["revision"], 2)

    def test_block_ids_must_be_unique_and_owned_by_this_session(self):
        other = TrainingSession.objects.create(
            title="Anderer Plan", date=date(2030, 1, 1), start_time=time(18), end_time=time(20)
        )
        foreign = TrainingBlock.objects.create(session=other, title="Fremd")
        for block_id in (foreign.pk, "1", True):
            data = self.payload()
            data["blocks"][0]["id"] = block_id
            self.assertEqual(self.save(data).status_code, 400)
        data = self.payload()
        data["blocks"] *= 2
        self.assertEqual(self.save(data).status_code, 400)
        self.assert_unchanged()

    def test_foreign_groups_or_changed_block_session_cannot_be_smuggled_in(self):
        for fields in ({"group_ids": [self.foreign_group.pk]}, {"session": self.session.pk + 1}):
            data = self.payload()
            data["blocks"][0].update(fields)
            self.assertEqual(self.save(data).status_code, 400)
        self.assert_unchanged()

    def test_can_shorten_term_and_blocks_in_same_transaction(self):
        data = self.payload()
        data["session"]["end_time"] = "18:15:00"
        data["blocks"][0].update(duration_minutes=15, start_offset_minutes=0)
        self.assertEqual(self.save(data).status_code, 200)

    def test_new_blocks_and_explicit_removal_are_part_of_same_snapshot(self):
        response = self.save(self.payload([{"title": "Neu", "duration_minutes": 15}]))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(TrainingBlock.objects.filter(pk=self.block.pk).exists())
        self.assertEqual(response.data["blocks"][0]["title"], "Neu")

    def test_legacy_writes_invalidate_loaded_plan(self):
        for path, values in (
            (f"/api/v1/training/blocks/{self.block.pk}/move/", {"start_offset_minutes": 10}),
            (f"/api/v1/training/blocks/{self.block.pk}/", {"content": "Geändert"}),
            (f"/api/v1/training/sessions/{self.session.pk}/", {"title": "Geändert"}),
        ):
            self.assertEqual(self.client.patch(path, values, format="json").status_code, 200)
            self.assertEqual(self.save(self.payload()).status_code, 409)
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 4)
        response = self.client.post(
            "/api/v1/training/blocks/", {"session": self.session.pk, "title": "Neu"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.delete(f"/api/v1/training/blocks/{response.data['id']}/").status_code, 204)
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 6)

    def test_global_training_right_is_still_limited_to_assigned_department(self):
        user = get_user_model().objects.create_user(username="assigned-planner")
        user.user_permissions.add(Permission.objects.get(codename="can_manage_training"))
        UserDepartmentRole.objects.create(user=user, department=self.department)
        self.client.force_authenticate(user)
        self.assertEqual(self.save(self.payload()).status_code, 200)
        data = self.payload(revision=2)
        data["session"].update(department=self.other_department.pk, group_ids=[])
        data["blocks"] = []
        self.assertEqual(self.save(data).status_code, 400)
        self.session.refresh_from_db()
        self.assertEqual(self.session.department_id, self.department.pk)

    def test_staff_without_training_right_cannot_read_conflict_or_write(self):
        user = get_user_model().objects.create_user(username="staff-no-training", is_staff=True)
        self.client.force_authenticate(user)
        self.assertEqual(self.save(self.payload(revision=100)).status_code, 403)
        self.assert_unchanged()
