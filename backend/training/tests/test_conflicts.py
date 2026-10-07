from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, RoleTemplate, UserDepartmentRole
from inventory.models import Item, Stock, StorageLocation, Transaction
from members.models import Group
from training.models import TrainingBlock, TrainingBlockMaterial, TrainingSession


class ConflictTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from io import StringIO

        from django.core.management import call_command

        call_command("seed_role_templates", stdout=StringIO())

    def setUp(self):
        User = get_user_model()
        self.department = Department.objects.create(name="Konflikte", code="conflicts")
        self.hidden = Department.objects.create(name="Verborgen", code="conflicts-hidden")
        self.planner = User.objects.create_user(username="konflikt-planer")
        UserDepartmentRole.objects.create(user=self.planner, department=self.department).groups.add(
            RoleTemplate.objects.get(key="training_planner").group
        )
        self.client = APIClient()
        self.client.force_authenticate(self.planner)
        self.trainer = User.objects.create_user(username="trainer", first_name="Toni", last_name="Trainer")
        UserDepartmentRole.objects.create(user=self.trainer, department=self.department)
        UserDepartmentRole.objects.create(user=self.trainer, department=self.hidden)
        self.red = Group.objects.create(name="Rot", department=self.department)
        self.blue = Group.objects.create(name="Blau", department=self.department)
        self.hose = Item.objects.create(name="C-Schlauch", department=self.department)
        store = StorageLocation.objects.create(name="Lager")
        member_store = StorageLocation.objects.create(name="Spind", is_member=True)
        Transaction.objects.create(transaction_type="IN", item=self.hose, target=store, quantity=3)
        Transaction.objects.create(transaction_type="IN", item=self.hose, target=member_store, quantity=5)
        self.session = TrainingSession.objects.create(
            title="Abend", date=date(2099, 9, 1), start_time=time(18), end_time=time(20), department=self.department
        )
        self.session.groups.set([self.red, self.blue])
        self.url = f"/api/v1/training/sessions/{self.session.pk}"

    def draft(self, *blocks, status=None, justification=None):
        session = {
            "title": "Abend",
            "date": "2099-09-01",
            "start_time": "18:00",
            "end_time": "20:00",
            "department": self.department.pk,
            "group_ids": [self.red.pk, self.blue.pk],
        }
        if status:
            session["status"] = status
        if justification is not None:
            session["publish_justification"] = justification
        return {"session": session, "blocks": list(blocks)}

    def block(self, title, offset, duration=30, groups=(), **extra):
        return {
            "title": title,
            "start_offset_minutes": offset,
            "duration_minutes": duration,
            "group_ids": list(groups),
            **extra,
        }

    def check(self, *blocks):
        response = self.client.post(f"{self.url}/check_plan/", self.draft(*blocks), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["warnings"]

    def test_group_overlaps_and_shared_blocks(self):
        warnings = self.check(
            self.block("Knoten", 0, groups=[self.red.pk]),
            self.block("Leinen", 15, groups=[self.red.pk]),
            self.block("Schläuche", 0, groups=[self.blue.pk]),
        )
        self.assertEqual([w["code"] for w in warnings], ["group"])
        self.assertIn("Rot", warnings[0]["message"])
        self.assertIn("18:15–18:30", warnings[0]["message"])
        # A block for all groups overlaps every group block.
        warnings = self.check(self.block("Begrüßung", 0), self.block("Schläuche", 10, groups=[self.blue.pk]))
        self.assertIn("Blau", warnings[0]["message"])
        # Sequential blocks are fine; nothing is saved by checking.
        self.assertEqual(self.check(self.block("A", 0), self.block("B", 30)), [])
        self.assertFalse(TrainingBlock.objects.exists())

    def test_instructor_and_location_conflicts_within_and_across_exercises(self):
        warnings = self.check(
            self.block("Station 1", 0, groups=[self.red.pk], instructor_ids=[self.trainer.pk], location="Hof"),
            self.block("Station 2", 0, groups=[self.blue.pk], instructor_ids=[self.trainer.pk], location=" hof "),
        )
        self.assertEqual(sorted(w["code"] for w in warnings), ["instructor", "location"])
        self.assertIn("Toni Trainer", next(w for w in warnings if w["code"] == "instructor")["message"])

        visible = TrainingSession.objects.create(
            title="Parallelübung",
            date=date(2099, 9, 1),
            start_time=time(19),
            end_time=time(21),
            department=self.department,
        )
        b = TrainingBlock.objects.create(session=visible, title="Hydrant", duration_minutes=30, location="Hof")
        b.instructors.add(self.trainer)
        hidden = TrainingSession.objects.create(
            title="Geheim", date=date(2099, 9, 1), start_time=time(18), end_time=time(19), department=self.hidden
        )
        hb = TrainingBlock.objects.create(session=hidden, title="Geheimer Block", duration_minutes=60)
        hb.instructors.add(self.trainer)
        cancelled = TrainingSession.objects.create(
            title="Abgesagt",
            date=date(2099, 9, 1),
            start_time=time(18),
            end_time=time(20),
            department=self.department,
            status="cancelled",
        )
        TrainingBlock.objects.create(session=cancelled, title="Weg", duration_minutes=120, location="Hof")
        warnings = self.check(self.block("Übung", 0, 120, instructor_ids=[self.trainer.pk], location="Hof"))
        messages = " | ".join(w["message"] for w in warnings)
        self.assertIn("„Parallelübung“", messages)
        self.assertIn("einer anderen Übung (nicht sichtbar)", messages)
        self.assertNotIn("Geheim", messages)
        self.assertNotIn("Abgesagt", messages)
        others = [w["other_session"] for w in warnings if w["other_session"]]
        self.assertEqual({o["id"] for o in others}, {visible.pk})

    def test_repeated_clashes_with_another_exercise_form_one_warning(self):
        parallel = TrainingSession.objects.create(
            title="Parallelübung",
            date=date(2099, 9, 1),
            start_time=time(18),
            end_time=time(21),
            department=self.department,
        )
        b = TrainingBlock.objects.create(session=parallel, title="Hydrant", duration_minutes=120, location="Station 1")
        b.instructors.add(self.trainer)
        warnings = self.check(
            self.block("Runde 1", 0, 25, instructor_ids=[self.trainer.pk], location="Station 1"),
            self.block("Runde 2", 30, 25, instructor_ids=[self.trainer.pk], location="station  1"),
        )
        self.assertEqual(sorted(w["code"] for w in warnings), ["instructor", "location"])
        instructor = next(w for w in warnings if w["code"] == "instructor")
        self.assertIn("18:00–18:25 „Runde 1“; 18:30–18:55 „Runde 2“", instructor["message"])
        self.assertIn("„Parallelübung“ (18:00–21:00)", instructor["message"])
        self.assertEqual(len(instructor["blocks"]), 2)
        self.assertIn("Ort „Station 1“", next(w for w in warnings if w["code"] == "location")["message"])

    def test_material_shortage_ignores_member_stock_and_counts_other_exercises(self):
        material = [{"item": self.hose.pk, "quantity": 2}]
        warnings = self.check(
            self.block("A", 0, groups=[self.red.pk], materials=material),
            self.block("B", 30, groups=[self.red.pk], materials=material),
        )
        self.assertEqual(warnings, [], "sequential use of 2 of 3 is fine")
        warnings = self.check(
            self.block("A", 0, groups=[self.red.pk], materials=material),
            self.block("B", 0, groups=[self.blue.pk], materials=material),
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("gleichzeitig 4 benötigt, rechnerisch 3 verfügbar", warnings[0]["message"])
        hidden = TrainingSession.objects.create(
            title="Geheim", date=date(2099, 9, 1), start_time=time(18), end_time=time(19), department=self.hidden
        )
        hb = TrainingBlock.objects.create(session=hidden, title="X", duration_minutes=60)
        TrainingBlockMaterial.objects.create(block=hb, item=self.hose, quantity=2, label="C-Schlauch")
        warnings = self.check(self.block("A", 0, materials=material))
        self.assertIn("inkl. Bedarf aus anderen Übungen (teilweise nicht sichtbar)", warnings[0]["message"])
        self.assertEqual(Stock.objects.filter(item=self.hose).count(), 2)

    def test_publishing_with_warnings_requires_and_stores_justification(self):
        blocks = [self.block("A", 0), self.block("B", 0)]
        payload = {"expected_revision": 1, **self.draft(*blocks, status="published")}
        response = self.client.put(f"{self.url}/plan/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("publish_justification", response.data)
        self.assertTrue(response.data["warnings"])
        self.session.refresh_from_db()
        self.assertEqual((self.session.status, self.session.revision), ("draft", 1))
        payload = {
            "expected_revision": 1,
            **self.draft(*blocks, status="published", justification="Gemeinsamer Auftakt gewollt"),
        }
        response = self.client.put(f"{self.url}/plan/", payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["publish_justification"], "Gemeinsamer Auftakt gewollt")
        self.assertTrue(response.data["publish_warnings"])
        # Saving an already published plan does not ask again.
        payload = {"expected_revision": 2, **self.draft(*blocks, status="published")}
        self.assertEqual(self.client.put(f"{self.url}/plan/", payload, format="json").status_code, 200)

    def test_single_status_change_checks_saved_plan(self):
        TrainingBlock.objects.create(session=self.session, title="A", duration_minutes=30)
        TrainingBlock.objects.create(session=self.session, title="B", duration_minutes=30)
        response = self.client.patch(f"{self.url}/", {"status": "published"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.client.get(f"{self.url}/conflicts/").data["warnings"]), 1)
        response = self.client.patch(
            f"{self.url}/", {"status": "published", "publish_justification": "Bewusst"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_publishing_without_warnings_needs_no_justification(self):
        payload = {"expected_revision": 1, **self.draft(self.block("A", 0), status="published")}
        response = self.client.put(f"{self.url}/plan/", payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["publish_justification"], response.data["publish_warnings"]), ("", []))

    def test_invalid_draft_is_rejected_and_readers_cannot_check(self):
        response = self.client.post(f"{self.url}/check_plan/", self.draft(self.block("A", 110, 30)), format="json")
        self.assertEqual(response.status_code, 400)
        reader = get_user_model().objects.create_user(username="nur-leser")
        UserDepartmentRole.objects.create(user=reader, department=self.department).groups.add(
            RoleTemplate.objects.get(key="supervisor").group
        )
        TrainingSession.objects.filter(pk=self.session.pk).update(status="published")
        self.client.force_authenticate(reader)
        self.assertEqual(self.client.get(f"{self.url}/conflicts/").status_code, 403)
        self.assertEqual(self.client.post(f"{self.url}/check_plan/", self.draft(), format="json").status_code, 403)
