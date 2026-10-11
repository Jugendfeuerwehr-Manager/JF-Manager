"""PART-04.2: places per position, "beliebig", waiting list per position and moving up."""

from datetime import date, timedelta
from unittest import mock

from django.test import TestCase

from departments.models import Department
from participation import service, signals
from participation.models import Registration, Slot
from participation.service import ParticipationError
from qualifications.models import Qualification, QualificationType

from .helpers import berlin, configure, make_member, make_session

NOW = berlin(2030, 3, 1, 12)


def has(qtype):
    return {"v": 1, "match": "all", "rules": [{"kind": "qualification", "op": "has_any", "values": [qtype.pk]}]}


class SlotAllocationBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="A", code="a")
        cls.leader_q = QualificationType.objects.create(name="Gruppenführer")

    def setUp(self):
        self.session = make_session(self.dept)
        self.participation = configure(self.session, mode="opt_in")
        self.tick = 0

    def slot(self, label, low, high, rule=None, position=0):
        slot = Slot.objects.create(
            participation=self.participation,
            label=label,
            min_count=low,
            max_count=high,
            rule=rule or {},
            position=position,
        )
        self.participation.max_participants = sum(s.max_count for s in self.participation.slots.all()) + (
            self.participation.extra_places or 0
        )
        self.participation.save()
        return slot

    def member(self, name, leader=False):
        member = make_member(self.dept, name)
        if leader:
            Qualification.objects.create(type=self.leader_q, member=member, date_acquired=date(2020, 1, 1))
        return member

    def register(self, member, slot=None, target="registered", source="staff", **kw):
        self.tick += 1
        return service.set_registration(
            self.session.pk,
            member.pk,
            target,
            actor=None,
            source=source,
            slot=getattr(slot, "pk", slot),
            now=NOW + timedelta(minutes=self.tick),
            **kw,
        )[0]

    def cancel(self, member):
        self.tick += 1
        return service.set_registration(
            self.session.pk, member.pk, "cancelled", actor=None, source="staff", now=NOW + timedelta(minutes=self.tick)
        )[0]

    def reload(self, member):
        return Registration.objects.get(session=self.session, member=member)


class ChosenPositionTests(SlotAllocationBase):
    def test_chosen_position_is_taken_then_waitlisted_for_it(self):
        crew = self.slot("Trupp", 1, 1)
        self.slot("Melder", 0, 1, position=1)
        first = self.register(self.member("Ada"), crew)
        self.assertEqual((first.state, first.slot_id, first.preferred_slot_id), ("registered", crew.pk, crew.pk))
        second = self.register(self.member("Ben"), crew)
        self.assertEqual((second.state, second.slot_id, second.preferred_slot_id), ("waitlisted", None, crew.pk))

    def test_unsuitable_chosen_position_is_refused_with_the_position_named(self):
        lead = self.slot("Wachführung", 1, 1, has(self.leader_q))
        with self.assertRaises(ParticipationError) as caught:
            self.register(self.member("Ada"), lead)
        self.assertEqual(caught.exception.code, "not_eligible")
        self.assertEqual(caught.exception.reasons, ["Position ‚Wachführung‘: Qualifikation ‚Gruppenführer‘ fehlt"])

    def test_unknown_position_is_400(self):
        other = make_session(self.dept, title="Andere")
        foreign = Slot.objects.create(participation=configure(other, mode="opt_in"), label="X", max_count=1)
        self.slot("Trupp", 0, 1)
        with self.assertRaises(ParticipationError) as caught:
            self.register(self.member("Ada"), foreign)
        self.assertEqual((caught.exception.code, caught.exception.status), ("invalid", 400))

    def test_nobody_without_a_suitable_position(self):
        self.slot("Wachführung", 1, 1, has(self.leader_q))
        with self.assertRaises(ParticipationError) as caught:
            self.register(self.member("Ada"))
        self.assertEqual(caught.exception.code, "not_eligible")
        self.assertIn("Position ‚Wachführung‘", caught.exception.reasons[0])


class AnyPositionTests(SlotAllocationBase):
    def test_positions_below_minimum_come_first(self):
        crew = self.slot("Trupp", 1, 3)
        guard = self.slot("Melder", 1, 1, position=1)
        self.register(self.member("Ada"), crew)
        second = self.register(self.member("Ben"))
        self.assertEqual(second.slot_id, guard.pk)  # Trupp already has its minimum
        third = self.register(self.member("Cem"))
        self.assertEqual(third.slot_id, crew.pk)

    def test_scarce_position_first(self):
        crew = self.slot("Trupp", 1, 2)
        lead = self.slot("Wachführung", 1, 1, has(self.leader_q), position=1)
        for name in ("Ada", "Ben", "Cem"):
            self.member(name)
        leader = self.member("Lea", leader=True)
        self.assertEqual(self.register(leader).slot_id, lead.pk)  # 1 candidate for lead, 4 for crew
        self.assertEqual(self.register(self.member("Dora")).slot_id, crew.pk)

    def test_order_of_positions_breaks_ties(self):
        first = self.slot("Erste", 0, 1)
        self.slot("Zweite", 0, 1, position=1)
        self.assertEqual(self.register(self.member("Ada")).slot_id, first.pk)

    def test_extra_places_take_people_without_free_position(self):
        self.participation.extra_places = 1
        self.participation.save()
        self.slot("Trupp", 0, 1)
        self.register(self.member("Ada"))
        guest = self.register(self.member("Ben"))
        self.assertEqual((guest.state, guest.slot_id), ("registered", None))
        self.assertEqual(self.register(self.member("Cem")).state, "waitlisted")

    def test_not_suitable_for_a_position_but_extra_places(self):
        self.participation.extra_places = 2
        self.participation.save()
        self.slot("Wachführung", 1, 1, has(self.leader_q))
        guest = self.register(self.member("Ada"))
        self.assertEqual((guest.state, guest.slot_id), ("registered", None))


class WaitlistPerPositionTests(SlotAllocationBase):
    def test_moving_up_into_the_freed_position(self):
        crew = self.slot("Trupp", 0, 1)
        guard = self.slot("Melder", 0, 1, position=1)
        ada, ben, cem, dora = (self.member(n) for n in ("Ada", "Ben", "Cem", "Dora"))
        self.register(ada, crew)
        self.register(ben, guard)
        self.register(cem, guard)  # waits for Melder only
        self.register(dora)  # waits for any position
        self.assertEqual(service.waitlist_position(self.reload(cem)), 1)
        self.assertEqual(service.waitlist_position(self.reload(dora)), 2)
        self.cancel(ada)  # Trupp frees: Cem waits for Melder only, Dora moves up
        self.assertEqual(self.reload(cem).state, "waitlisted")
        self.assertEqual((self.reload(dora).state, self.reload(dora).slot_id), ("registered", crew.pk))
        self.cancel(ben)
        self.assertEqual((self.reload(cem).state, self.reload(cem).slot_id), ("registered", guard.pk))

    def test_first_waiting_person_who_does_not_suit_is_skipped(self):
        lead = self.slot("Wachführung", 1, 1, has(self.leader_q))
        holder = self.member("Lea", leader=True)
        self.register(holder, lead)
        early = self.member("Ada")
        Qualification.objects.create(type=self.leader_q, member=early, date_acquired=date(2020, 1, 1))
        self.register(early, lead)
        late = self.member("Max", leader=True)
        self.register(late, lead)
        Qualification.objects.filter(member=early).delete()  # no longer suits the position
        self.cancel(holder)
        self.assertEqual(self.reload(early).state, "waitlisted")
        self.assertEqual(self.reload(late).state, "registered")

    def test_manual_waiting_list_announces_and_staff_move_people_up(self):
        self.participation.waitlist_mode = "manual"
        self.participation.save()
        crew = self.slot("Trupp", 0, 1)
        ada, ben = self.member("Ada"), self.member("Ben")
        self.register(ada, crew)
        self.register(ben, crew)
        received = []
        handler = mock.Mock(side_effect=lambda **kw: received.append(kw))
        signals.place_freed.connect(handler, dispatch_uid="test-place-freed")
        try:
            with self.captureOnCommitCallbacks(execute=True):
                self.cancel(ada)
        finally:
            signals.place_freed.disconnect(dispatch_uid="test-place-freed")
        self.assertEqual(self.reload(ben).state, "waitlisted")
        self.assertEqual((received[0]["slot_label"], received[0]["waiting"]), ("Trupp", 1))
        # the portal cannot move itself up, staff can
        self.assertEqual(self.register(ben, source="portal_member").state, "waitlisted")
        moved = self.register(ben)
        self.assertEqual((moved.state, moved.slot_id), ("registered", crew.pk))

    def test_raising_places_moves_people_up(self):
        crew = self.slot("Trupp", 0, 1)
        self.register(self.member("Ada"), crew)
        ben = self.member("Ben")
        self.register(ben, crew)
        Slot.objects.filter(pk=crew.pk).update(max_count=2)
        self.participation.max_participants = 2
        self.participation.save()
        service.promote_waitlist(self.session, self.participation, now=NOW)
        self.assertEqual(self.reload(ben).state, "registered")


class AssignmentWishTests(SlotAllocationBase):
    def test_application_keeps_the_wish(self):
        self.participation.mode = "assignment"
        self.participation.save()
        lead = self.slot("Wachführung", 1, 1, has(self.leader_q))
        crew = self.slot("Trupp", 0, 2, position=1)
        ada = self.register(self.member("Ada"), crew, target="applied")
        self.assertEqual((ada.state, ada.preferred_slot_id, ada.slot_id), ("applied", crew.pk, None))
        anyone = self.register(self.member("Ben"), target="applied")
        self.assertIsNone(anyone.preferred_slot_id)
        with self.assertRaises(ParticipationError) as caught:
            self.register(self.member("Cem"), lead, target="applied")
        self.assertEqual(caught.exception.code, "not_eligible")
