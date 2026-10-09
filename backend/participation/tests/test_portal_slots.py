"""PART-04.3: the portal shows free places per position and the own waiting place, never names (D6)."""

from datetime import date

from participation.models import Registration, Slot
from qualifications.models import Qualification, QualificationType

from .helpers import configure, make_member
from .test_portal_api import LIST, PortalBase, put_url


class PortalPositionTests(PortalBase):
    def setUp(self):
        super().setUp()
        self.participation = configure(self.session, mode="opt_in", max_participants=2)
        self.qtype = QualificationType.objects.create(name="Gruppenführer")
        rule = {
            "v": 1,
            "match": "all",
            "rules": [{"kind": "qualification", "op": "has_any", "values": [self.qtype.pk]}],
        }
        self.lead = Slot.objects.create(participation=self.participation, label="Wachführung", max_count=1, rule=rule)
        self.crew = Slot.objects.create(participation=self.participation, label="Trupp", max_count=1, position=1)

    def item(self, person):
        return self.client.get(LIST, {"person": person.pk}).json()["sessions"][0]

    def test_positions_with_free_places_and_suitability(self):
        other = make_member(self.dept, "Ida", self.group)
        Registration.objects.create(
            session=self.session,
            member=other,
            state="registered",
            slot=self.crew,
            source="staff",
            state_changed_at="2030-01-01T10:00:00Z",
        )
        item = self.item(self.mia)
        self.assertEqual(
            item["positions"],
            [
                {"id": self.lead.pk, "label": "Wachführung", "max": 1, "free": 1, "suits": False},
                {"id": self.crew.pk, "label": "Trupp", "max": 1, "free": 0, "suits": True},
            ],
        )
        self.assertNotIn("Ida", str(item))
        # only the crew position suits Mia and it is full: registering means the waiting list
        self.assertTrue(item["may_register"])
        response = self.client.put(put_url(self.session, self.mia), self.body("registered"), format="json")
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual((body["state"], body["waitlist_position"]), ("waitlisted", 1))

    def test_registering_for_a_chosen_position(self):
        Qualification.objects.create(type=self.qtype, member=self.mia, date_acquired=date(2020, 1, 1))
        response = self.client.put(
            put_url(self.session, self.mia), self.body("registered", slot=self.lead.pk), format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(
            (body["state"], body["slot_label"], body["preferred_slot"]), ("registered", "Wachführung", self.lead.pk)
        )

    def test_unsuitable_chosen_position_shows_the_reason(self):
        response = self.client.put(
            put_url(self.session, self.mia), self.body("registered", slot=self.lead.pk), format="json"
        )
        self.assertEqual((response.status_code, response.json()["code"]), (422, "not_eligible"))
        self.assertIn("Wachführung", response.json()["reasons"][0])

    def test_position_of_another_session_is_refused(self):
        response = self.client.put(put_url(self.session, self.mia), self.body("registered", slot=999999), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Registration.objects.filter(member=self.mia).exists())
