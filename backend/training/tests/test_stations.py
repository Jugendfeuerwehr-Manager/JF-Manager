from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from inventory.models import Item, ItemVariant, Stock, StorageLocation, Transaction
from training.models import TrainingBlock, TrainingSession, TrainingTemplate


class StationResourceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username="station-test")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.department = Department.objects.create(name="Stationen", code="stations")
        self.other = Department.objects.create(name="Andere", code="stations-other")
        self.trainer = User.objects.create_user(username="ausbilder", first_name="Alex", last_name="Ausbilder")
        UserDepartmentRole.objects.create(user=self.trainer, department=self.department)
        self.outsider = User.objects.create_user(username="fremd")
        UserDepartmentRole.objects.create(user=self.outsider, department=self.other)
        self.inactive = User.objects.create_user(username="inaktiv", is_active=False)
        UserDepartmentRole.objects.create(user=self.inactive, department=self.department)
        self.hose = Item.objects.create(name="C-Schlauch", department=self.department)
        self.shared = Item.objects.create(name="Pylon")
        self.foreign = Item.objects.create(name="Fremdgerät", department=self.other)
        self.jacket = Item.objects.create(name="Jacke", department=self.department, is_variant_parent=True)
        self.size = ItemVariant.objects.create(parent_item=self.jacket, variant_attributes={"größe": "164"})
        self.store = StorageLocation.objects.create(name="Lager")
        Transaction.objects.create(transaction_type="IN", item=self.hose, target=self.store, quantity=4)
        self.session = TrainingSession.objects.create(
            title="Stationsabend",
            date=date(2099, 6, 1),
            start_time=time(18),
            end_time=time(20),
            department=self.department,
        )
        self.url = f"/api/v1/training/sessions/{self.session.pk}"

    def station(self, **changes):
        return {
            "title": "Wasserentnahme",
            "kind": "station",
            "location": "Hydrant Nord",
            "learning_objective": "Saugleitung kuppeln",
            "safety_notes": "Handschuhe tragen",
            "content": "<p>Ablauf</p>",
            "duration_minutes": 20,
            "instructor_ids": [self.trainer.pk],
            "materials": [{"item": self.hose.pk, "quantity": 2}, {"label": "Kreide", "quantity": 1}],
            **changes,
        }

    def put(self, *blocks):
        self.session.refresh_from_db()
        return self.client.put(
            f"{self.url}/plan/",
            {
                "expected_revision": self.session.revision,
                "session": {
                    "title": "Stationsabend",
                    "date": "2099-06-01",
                    "start_time": "18:00",
                    "end_time": "20:00",
                    "department": self.department.pk,
                },
                "blocks": list(blocks),
            },
            format="json",
        )

    def test_station_fields_instructors_and_materials_are_saved_atomically(self):
        response = self.put(self.station())
        self.assertEqual(response.status_code, 200, response.data)
        block = response.data["blocks"][0]
        self.assertEqual(
            (block["kind"], block["location"], block["learning_objective"], block["safety_notes"]),
            ("station", "Hydrant Nord", "Saugleitung kuppeln", "Handschuhe tragen"),
        )
        self.assertEqual(block["instructors"], [{"id": self.trainer.pk, "name": "Alex Ausbilder"}])
        self.assertEqual(
            [(m["item"], m["quantity"], m["label"]) for m in block["materials"]],
            [(self.hose.pk, 2, "C-Schlauch"), (None, 1, "Kreide")],
        )
        # Material needs never touch stock.
        self.assertEqual(Stock.objects.get(item=self.hose).quantity, 4)
        # Replacing the plan replaces the material rows, it does not append.
        block_id = block["id"]
        response = self.put(self.station(id=block_id, materials=[{"variant": self.size.pk, "quantity": 3}]))
        self.assertEqual(response.status_code, 200, response.data)
        materials = response.data["blocks"][0]["materials"]
        self.assertEqual(
            [(m["item"], m["variant"], m["quantity"]) for m in materials], [(self.jacket.pk, self.size.pk, 3)]
        )
        self.assertIn("164", materials[0]["label"])

    def test_invalid_instructors_and_materials_are_rejected_without_changes(self):
        cases = [
            self.station(instructor_ids=[self.outsider.pk]),
            self.station(instructor_ids=[self.inactive.pk]),
            self.station(materials=[{"item": self.foreign.pk, "quantity": 1}]),
            self.station(materials=[{"item": self.hose.pk, "variant": self.size.pk}]),
            self.station(materials=[{"quantity": 1}]),
            self.station(materials=[{"item": self.hose.pk, "quantity": 0}]),
            self.station(kind="party"),
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.put(payload).status_code, 400)
        self.assertFalse(TrainingBlock.objects.exists())
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 1)
        self.assertEqual(self.put(self.station(materials=[{"item": self.shared.pk}])).status_code, 200)

    def test_options_are_minimal_and_limited_to_planners(self):
        instructors = self.client.get(f"{self.url}/instructor_options/").data
        self.assertEqual(instructors, [{"id": self.trainer.pk, "name": "Alex Ausbilder"}])
        options = self.client.get(f"{self.url}/material_options/").data
        self.assertEqual({row["name"] for row in options}, {"C-Schlauch", "Pylon", "Jacke"})
        self.assertEqual(next(r for r in options if r["name"] == "Jacke")["variants"][0]["id"], self.size.pk)
        self.assertEqual(
            [r["name"] for r in self.client.get(f"{self.url}/material_options/", {"search": "schl"}).data],
            ["C-Schlauch"],
        )
        reader = get_user_model().objects.create_user(username="leser")
        reader.user_permissions.add(Permission.objects.get(codename="view_trainingsession"))
        UserDepartmentRole.objects.create(user=reader, department=self.department)
        TrainingSession.objects.filter(pk=self.session.pk).update(status="published")
        self.client.force_authenticate(reader)
        self.assertEqual(self.client.get(f"{self.url}/instructor_options/").status_code, 403)
        self.assertEqual(self.client.get(f"{self.url}/material_options/").status_code, 403)

    def test_copy_template_and_series_carry_resources_independently(self):
        self.put(self.station())
        copy = self.client.post(f"{self.url}/copy/", {"date": "2099-07-01"}, format="json").data
        copied = TrainingBlock.objects.get(session_id=copy["id"])
        self.assertEqual((copied.kind, copied.location), ("station", "Hydrant Nord"))
        self.assertEqual(list(copied.instructors.all()), [self.trainer])
        self.assertEqual(copied.materials.count(), 2)
        original = TrainingBlock.objects.get(session=self.session)
        original.materials.all().delete()
        self.assertEqual(copied.materials.count(), 2)

        template_id = self.client.post(f"{self.url}/save_as_template/", {}, format="json").data["id"]
        template_block = TrainingTemplate.objects.get(pk=template_id).blocks.get()
        self.assertEqual(template_block.instructors.get(), self.trainer)
        # The trainer leaves the department before the template is used again.
        UserDepartmentRole.objects.filter(user=self.trainer).delete()
        created = self.client.post(
            f"/api/v1/training/templates/{template_id}/instantiate/", {"date": "2099-08-01"}, format="json"
        ).data
        block = TrainingBlock.objects.get(session_id=created["id"])
        self.assertFalse(block.instructors.exists())
        self.assertEqual(block.kind, "station")

    def test_material_change_is_reported_by_this_and_following(self):
        self.session.recurrence_rule = {"frequency": "WEEKLY", "end_date": "2099-06-15"}
        self.session.save()
        self.put(self.station())
        token = self.client.get(f"{self.url}/series_preview/").data["preview_token"]
        self.client.post(f"{self.url}/generate_series/", {"preview_token": token}, format="json")
        block_id = TrainingBlock.objects.get(session=self.session).pk
        self.put(self.station(id=block_id, materials=[{"item": self.hose.pk, "quantity": 5}]))
        preview = self.client.post(f"{self.url}/propagation_preview/", {}, format="json").data
        self.assertTrue(all(row["action"] == "update" for row in preview["occurrences"]))
        self.assertTrue(all(any(c.startswith("Ablauf") for c in row["changes"]) for row in preview["occurrences"]))

    def test_linked_station_key_is_kept_in_plan_copies_and_series(self):
        key = "6f1c2b9e-1d2a-4c55-9a7e-3c1f0b8e2d41"
        response = self.put(self.station(station_key=key), self.station(station_key=key, start_offset_minutes=30))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({b["station_key"] for b in response.data["blocks"]}, {key})
        self.assertEqual(self.put(self.station(station_key="kein-schlüssel")).status_code, 400)
        copy = self.client.post(f"{self.url}/copy/", {"date": "2099-07-01"}, format="json").data
        self.assertEqual(
            {str(k) for k in TrainingBlock.objects.filter(session_id=copy["id"]).values_list("station_key", flat=True)},
            {key},
        )
        self.session.recurrence_rule = {"frequency": "WEEKLY", "end_date": "2099-06-08"}
        self.session.save()
        token = self.client.get(f"{self.url}/series_preview/").data["preview_token"]
        generated = self.client.post(f"{self.url}/generate_series/", {"preview_token": token}, format="json")
        self.assertEqual(generated.status_code, 201, generated.data)
        child = TrainingBlock.objects.filter(session_id=generated.data["session_ids"][0])
        self.assertEqual({str(k) for k in child.values_list("station_key", flat=True)}, {key})
