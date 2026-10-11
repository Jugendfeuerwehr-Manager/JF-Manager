"""PART-04.1: positions, places and minimum staffing."""

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from participation import slots
from participation.models import Registration, SessionParticipation, Slot
from qualifications.models import QualificationType

from .helpers import configure, make_member, make_session
from .test_staff_api import StaffApiBase, url


class FakeSlot:
    def __init__(self, pk, label, low, high, position=0, rule=None):
        self.pk, self.label, self.min_count, self.max_count = pk, label, low, high
        self.position, self.rule = position, rule or {}


class FakeParticipation:
    def __init__(self, extra=None, low=None, high=None):
        self.extra_places, self.min_participants, self.max_participants = extra, low, high


class StaffingTests(SimpleTestCase):
    def setUp(self):
        self.lead = FakeSlot(1, "Wachführung", 1, 1, 0)
        self.crew = FakeSlot(2, "Truppmann/-frau", 2, 2, 1)
        self.guest = FakeSlot(3, "Hospitation", 0, 3, 2)

    def test_counts_fulfilled_positions_and_names_what_is_missing(self):
        result = slots.staffing(FakeParticipation(), [self.lead, self.crew, self.guest], {2: 2})
        self.assertFalse(result["met"])
        self.assertEqual((result["required"], result["fulfilled"]), (2, 1))
        self.assertEqual(result["missing"], [{"label": "Wachführung", "count": 1}])
        self.assertEqual(result["text"], "Mindestbesetzung: 1 von 2 erfüllt – es fehlt 1× Wachführung")
        self.assertEqual([row["free"] for row in result["slots"]], [1, 0, 3])

    def test_met_when_every_minimum_is_reached(self):
        result = slots.staffing(FakeParticipation(), [self.lead, self.crew], {1: 1, 2: 2})
        self.assertTrue(result["met"])
        self.assertEqual(result["text"], "Mindestbesetzung: 2 von 2 erfüllt")

    def test_nothing_required(self):
        self.assertTrue(slots.staffing(FakeParticipation(), [self.guest], {})["met"])
        self.assertIsNone(slots.staffing(FakeParticipation(), [], {}))

    def test_minimum_without_positions(self):
        result = slots.staffing(FakeParticipation(low=5), [], {None: 3})
        self.assertEqual((result["met"], result["missing"]), (False, [{"label": "Teilnehmende", "count": 2}]))
        self.assertEqual(result["text"], "Mindestzahl: 3 von 5 erreicht – es fehlen 2")
        self.assertTrue(slots.staffing(FakeParticipation(low=2), [], {None: 3})["met"])

    def test_capacity_is_derived_from_positions(self):
        self.assertEqual(slots.capacity(FakeParticipation(extra=2), [self.lead, self.crew]), 5)
        self.assertEqual(slots.capacity(FakeParticipation(high=7), []), 7)


class SlotModelTests(TestCase):
    def test_constraints(self):
        from departments.models import Department

        session = make_session(Department.objects.create(name="A", code="a"))
        participation = configure(session, mode="opt_in")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Slot.objects.create(participation=participation, label="x", min_count=3, max_count=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Slot.objects.create(participation=participation, label="x", min_count=0, max_count=0)
        slot = Slot.objects.create(participation=participation, label="ok", min_count=1, max_count=2)
        self.assertEqual(list(participation.slots.all()), [slot])


class SlotConfigApiTests(StaffApiBase):
    def put(self, body, user=None):
        client = self.as_user(user) if user else self.client
        return client.put(url(self.session), body, format="json")

    def positions(self, **extra):
        return {
            "revision": 0,
            "mode": "opt_in",
            "slots": [
                {"label": "Wachführung", "min": 1, "max": 1},
                {"label": "Truppmann/-frau", "min": 2, "max": 2},
            ],
            **extra,
        }

    def test_positions_are_saved_in_order_and_derive_the_maximum(self):
        response = self.put(self.positions(extra_places=2, max_participants=99))
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual([s["label"] for s in body["slots"]], ["Wachführung", "Truppmann/-frau"])
        self.assertEqual((body["max_participants"], body["capacity"], body["extra_places"]), (5, 5, 2))
        self.assertEqual(
            body["staffing"]["text"], "Mindestbesetzung: 0 von 2 erfüllt – es fehlt 1× Wachführung, 2× Truppmann/-frau"
        )
        self.assertEqual(SessionParticipation.objects.get().max_participants, 5)

    def test_update_keeps_ids_reorders_and_removes(self):
        body = self.put(self.positions()).json()
        lead, crew = body["slots"]
        response = self.put(
            {
                "revision": body["revision"],
                "slots": [
                    {"id": crew["id"], "label": "Trupp", "min": 1, "max": 3},
                    {"label": "Melder", "min": 0, "max": 1},
                ],
            }
        )
        self.assertEqual(response.status_code, 200, response.content)
        slots_after = response.json()["slots"]
        first = slots_after[0]
        self.assertEqual((first["id"] == crew["id"], first["label"], first["position"]), (True, "Trupp", 0))
        self.assertFalse(Slot.objects.filter(pk=lead["id"]).exists())
        self.assertEqual(response.json()["max_participants"], 4)

    def test_slot_rule_is_validated_and_summarised(self):
        qtype = QualificationType.objects.create(name="Gruppenführer")
        rule = {"v": 1, "match": "all", "rules": [{"kind": "qualification", "op": "has_all", "values": [qtype.pk]}]}
        response = self.put(self.positions(slots=[{"label": "Wachführung", "min": 1, "max": 1, "rule": rule}]))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["slots"][0]["rule_summary"], "Gruppenführer")
        bad = {"v": 1, "match": "all", "rules": [{"kind": "age", "op": "between", "min": 9, "max": 5}]}
        response = self.put({"revision": 1, "slots": [{"label": "Wachführung", "min": 1, "max": 1, "rule": bad}]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["slots"][0]["rule"], {"rules[0].max": "Mindestalter größer als Höchstalter"})

    def test_validation(self):
        cases = {
            "opt_out": {"mode": "opt_out", "slots": [{"label": "A", "min": 0, "max": 1}]},
            "min_above_max": {"mode": "opt_in", "slots": [{"label": "A", "min": 2, "max": 1}]},
            "duplicate": {
                "mode": "opt_in",
                "slots": [{"label": "A", "min": 0, "max": 1}, {"label": "a", "min": 0, "max": 1}],
            },
            "markup": {"mode": "opt_in", "slots": [{"label": "<b>A</b>", "min": 0, "max": 1}]},
            "zero_places": {"mode": "opt_in", "slots": [{"label": "A", "min": 0, "max": 0}]},
            "too_many": {"mode": "opt_in", "slots": [{"label": f"P{i}", "min": 0, "max": 1} for i in range(31)]},
        }
        for name, extra in cases.items():
            with self.subTest(name):
                response = self.put({"revision": 0, **extra})
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Slot.objects.exists())

    def test_taken_positions_cannot_lose_places(self):
        body = self.put(self.positions()).json()
        lead = body["slots"][0]
        Registration.objects.create(
            session=self.session,
            member=self.mia,
            state="registered",
            slot_id=lead["id"],
            source="staff",
            state_changed_at=self.session_start(),
        )
        response = self.put({"revision": body["revision"], "slots": body["slots"][1:]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("noch besetzt", str(response.json()["slots"]))
        self.assertTrue(Slot.objects.filter(pk=lead["id"]).exists())
        self.assertEqual(SessionParticipation.objects.get().revision, body["revision"])

    def test_switching_to_opt_out_removes_positions(self):
        body = self.put(self.positions()).json()
        response = self.put({"revision": body["revision"], "mode": "opt_out", "max_participants": None})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()["slots"], response.json()["max_participants"]), ([], None))

    def test_registrations_overview_reports_staffing(self):
        body = self.put(self.positions()).json()
        Registration.objects.create(
            session=self.session,
            member=self.mia,
            state="registered",
            slot_id=body["slots"][1]["id"],
            source="staff",
            state_changed_at=self.session_start(),
        )
        overview = self.client.get(url(self.session, "registrations/")).json()
        self.assertEqual([s["seated"] for s in overview["slots"]], [0, 1])
        self.assertEqual(overview["staffing"]["fulfilled"], 0)
        mia = next(m for m in overview["members"] if m["member_id"] == self.mia.pk)
        self.assertEqual(mia["registration"]["slot"], body["slots"][1]["id"])

    def test_permissions(self):
        self.assertEqual(self.put(self.positions(), user=self.other_planner).status_code, 403)
        self.assertEqual(self.put(self.positions(), user=self.reader).status_code, 403)
        self.assertEqual(self.put(self.positions(), user=self.portal).status_code, 403)
        self.assertFalse(Slot.objects.exists())

    def session_start(self):
        from participation.service import session_start

        return session_start(self.session)


class SlotsWithoutConfigurationTests(TestCase):
    def test_unsaved_configuration_has_no_positions(self):
        from departments.models import Department

        dept = Department.objects.create(name="A", code="a")
        make_member(dept)
        self.assertEqual(slots.slots_for(SessionParticipation()), [])
