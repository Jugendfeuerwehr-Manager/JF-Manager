from datetime import UTC, datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from departments.models import Department
from members.models import Group
from participation import service
from participation.models import Registration, RegistrationEvent, SessionParticipation
from participation.signals import session_changed

from .helpers import configure, future_day, make_member, make_session
from .test_portal_api import LIST, PortalBase, put_url


def local(day, hour=0, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def register(session, member, state, **kw):
    return Registration.objects.create(
        session=session, member=member, state=state, source="staff", state_changed_at=timezone.now(), **kw
    )


class SessionChangedBase(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="A", code="a")
        self.group = Group.objects.create(name="Rot", department=self.dept)
        self.mia = make_member(self.dept, "Mia", self.group)
        self.ole = make_member(self.dept, "Ole", self.group)
        self.tom = make_member(self.dept, "Tom", self.group)
        self.day = future_day(15)
        self.session = make_session(self.dept, day=self.day, groups=[self.group], location="Halle")
        self.received = []

        def handler(sender, **kwargs):
            kwargs.pop("signal")
            self.received.append(kwargs)

        session_changed.connect(handler)
        self.addCleanup(session_changed.disconnect, handler)

    def save(self, session, **values):
        with self.captureOnCommitCallbacks(execute=True):
            for name, value in values.items():
                setattr(session, name, value)
            session.save()


class SessionChangedSignalTests(SessionChangedBase):
    def test_moved_payload_and_audience_in_opt_out(self):
        register(self.session, self.mia, "cancelled")
        register(self.session, self.ole, "registered")
        self.save(self.session, date=self.day + timedelta(days=1), start_time=time(17))
        [event] = self.received
        self.assertEqual(event["kind"], "moved")
        self.assertEqual(event["session"].pk, self.session.pk)
        self.assertEqual(
            event["old"], {"date": self.day, "start_time": time(18), "end_time": time(20), "place": "Halle"}
        )
        self.assertEqual(event["new"]["date"], self.day + timedelta(days=1))
        self.assertEqual(event["new"]["start_time"], time(17))
        # Expected target group minus cancelled: Ole (registered) and Tom (no row).
        self.assertEqual(event["member_ids"], sorted([self.ole.pk, self.tom.pk]))

    def test_place_only_is_changed_and_opt_in_audience_is_registrations(self):
        configure(self.session, mode="opt_in", max_participants=1)
        register(self.session, self.mia, "registered")
        register(self.session, self.ole, "waitlisted")
        register(self.session, self.tom, "cancelled")
        self.save(self.session, location="Wache")
        [event] = self.received
        self.assertEqual(event["kind"], "changed")
        self.assertEqual((event["old"]["place"], event["new"]["place"]), ("Halle", "Wache"))
        self.assertEqual(event["member_ids"], sorted([self.mia.pk, self.ole.pk]))

    def test_cancelled_is_sent_with_frozen_registrations(self):
        configure(self.session, mode="opt_in")
        register(self.session, self.mia, "registered")
        self.save(self.session, status="cancelled")
        [event] = self.received
        self.assertEqual(event["kind"], "cancelled")
        self.assertEqual(event["member_ids"], [self.mia.pk])
        self.assertEqual(Registration.objects.get(member=self.mia).state, "registered")

    def test_untouched_fields_drafts_past_and_hidden_do_not_fire(self):
        self.save(self.session, title="Neuer Titel")
        draft = make_session(self.dept, day=self.day, groups=[self.group], status="draft")
        self.save(draft, date=self.day + timedelta(days=2))
        self.save(draft, status="cancelled")
        past = make_session(self.dept, day=timezone.localdate() - timedelta(days=1), groups=[self.group])
        self.save(past, location="Anderswo")
        self.save(past, status="cancelled")
        hidden = make_session(self.dept, day=self.day, groups=[self.group])
        configure(hidden, portal_visible=False)
        self.save(hidden, location="Anderswo")
        self.assertEqual(self.received, [])

    def test_update_fields_without_tracked_fields_is_ignored(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.session.title = "Nur Titel"
            self.session.save(update_fields=["title"])
        self.assertEqual(self.received, [])


class MoveKeepsRegistrationsTests(SessionChangedBase):
    def test_registrations_stay_and_derived_deadlines_follow_the_start(self):
        register(self.session, self.mia, "cancelled", reason_category="urlaub")
        register(self.session, self.ole, "registered")
        participation, _ = service.participation_for(self.session)
        before = service.deadlines(self.session, participation)
        self.save(self.session, date=self.day + timedelta(days=3))
        self.session.refresh_from_db()
        after = service.deadlines(self.session, service.participation_for(self.session)[0])
        # Offsets are real hours (a daylight-saving change in between is irrelevant).
        self.assertEqual(
            after.start.astimezone(UTC) - after.registration_closes_at.astimezone(UTC), timedelta(hours=48)
        )
        self.assertEqual(after.start.astimezone(UTC) - after.cancellation_closes_at.astimezone(UTC), timedelta(hours=2))
        self.assertGreater(after.start, before.start)
        self.assertEqual(
            dict(Registration.objects.values_list("member_id", "state")),
            {self.mia.pk: "cancelled", self.ole.pk: "registered"},
        )

    def test_explicit_deadlines_stay_but_are_capped_at_the_new_start(self):
        late = local(self.day, 17)
        early = local(self.day - timedelta(days=5), 12)
        configure(self.session, registration_closes_at=late, cancellation_closes_at=early)
        # Moving the service earlier pulls only the deadline that would lie behind the start.
        self.save(self.session, start_time=time(16), end_time=time(18))
        row = SessionParticipation.objects.get(session=self.session)
        self.assertEqual(row.registration_closes_at, local(self.day, 16))
        self.assertEqual(row.cancellation_closes_at, early)
        # Moving later does not touch explicit values.
        self.save(self.session, start_time=time(19), end_time=time(21))
        row.refresh_from_db()
        self.assertEqual(row.registration_closes_at, local(self.day, 16))


class ModeSwitchTests(SessionChangedBase):
    def switch(self, **values):
        row, _ = service.participation_for(self.session)
        previous = row.mode
        from participation import changes

        for name, value in values.items():
            setattr(row, name, value)
        if row.mode == "opt_out":
            row.max_participants = None
        row.save()
        return changes.apply_mode_change(self.session, previous, row)

    def state(self, member):
        return Registration.objects.get(member=member).state

    def test_opt_out_to_opt_in_keeps_everything(self):
        register(self.session, self.mia, "cancelled", reason_category="urlaub")
        register(self.session, self.ole, "registered")
        self.assertEqual(self.switch(mode="opt_in"), [])
        self.assertEqual((self.state(self.mia), self.state(self.ole)), ("cancelled", "registered"))
        self.assertFalse(Registration.objects.filter(member=self.tom).exists())
        self.assertEqual(
            service.participation_for(self.session)[0].mode, "opt_in"
        )  # Tom: no row -> "no response" in the portal

    def test_opt_in_to_opt_out_confirms_waitlist_and_keeps_history(self):
        configure(self.session, mode="opt_in", max_participants=1)
        register(self.session, self.mia, "registered")
        register(self.session, self.ole, "waitlisted")
        register(self.session, self.tom, "cancelled")
        changed = self.switch(mode="opt_out")
        self.assertEqual([r.member_id for r in changed], [self.ole.pk])
        self.assertEqual(
            (self.state(self.mia), self.state(self.ole), self.state(self.tom)), ("registered",) * 2 + ("cancelled",)
        )
        self.assertIsNone(SessionParticipation.objects.get(session=self.session).max_participants)
        event = RegistrationEvent.objects.get(registration__member=self.ole)
        self.assertEqual((event.from_state, event.to_state, event.via), ("waitlisted", "registered", "system"))

    def test_assignment_to_opt_in_respects_the_maximum(self):
        configure(self.session, mode="assignment", max_participants=1)
        register(self.session, self.mia, "assigned")
        register(self.session, self.ole, "applied")
        register(self.session, self.tom, "not_selected")
        self.switch(mode="opt_in")
        self.assertEqual(
            (self.state(self.mia), self.state(self.ole), self.state(self.tom)),
            ("registered", "waitlisted", "not_selected"),
        )

    def test_opt_in_to_assignment_turns_waitlist_into_applications(self):
        configure(self.session, mode="opt_in", max_participants=1)
        register(self.session, self.mia, "registered")
        register(self.session, self.ole, "waitlisted")
        self.switch(mode="assignment")
        self.assertEqual((self.state(self.mia), self.state(self.ole)), ("registered", "applied"))

    def test_staff_api_applies_the_switch(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser("root-x")
        configure(self.session, mode="opt_in", max_participants=1)
        register(self.session, self.ole, "waitlisted")
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user)
        url = f"/api/v1/participation/sessions/{self.session.pk}/config/"
        revision = client.get(url).json()["revision"]
        response = client.put(url, {"mode": "opt_out", "max_participants": None, "revision": revision}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.state(self.ole), "registered")


class CancelledSessionPortalTests(PortalBase):
    def test_cancelled_session_is_listed_frozen_without_actions(self):
        register(self.session, self.mia, "registered")
        self.session.status = "cancelled"
        self.session.save()
        [item] = self.client.get(LIST, {"person": self.mia.pk}).json()["sessions"]
        self.assertEqual((item["session_status"], item["state"]), ("cancelled", "registered"))
        self.assertEqual((item["may_register"], item["may_cancel"]), (False, False))
        self.assertEqual(item["cancel_blocked"]["code"], "not_open")
        response = self.client.put(put_url(self.session, self.mia), {"target": "cancelled"}, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(Registration.objects.get(member=self.mia).state, "registered")


class AbsenceOverSeriesTests(PortalBase):
    def test_period_cancellation_covers_every_occurrence_of_a_series(self):
        root = self.session
        root.series_uuid = __import__("uuid").uuid4()
        root.save()
        children = []
        for weeks in (1, 2, 3):
            child = make_session(
                self.dept,
                day=root.date + timedelta(weeks=weeks),
                groups=[self.group],
                series_parent=root,
                series_uuid=root.series_uuid,
            )
            children.append(child)
        payload = {
            "person": self.mia.pk,
            "from": (root.date + timedelta(days=3)).isoformat(),
            "to": (root.date + timedelta(weeks=3)).isoformat(),
        }
        preview = self.client.post("/api/v1/portal/absences/preview/", payload, format="json").json()
        self.assertEqual(preview["will_cancel"], 3)
        done = self.client.post("/api/v1/portal/absences/", payload, format="json").json()
        self.assertEqual(sorted(s["id"] for s in done["cancelled"]), sorted(c.pk for c in children))
        states_ = dict(Registration.objects.filter(member=self.mia).values_list("session_id", "state"))
        self.assertEqual(states_, {c.pk: "cancelled" for c in children})
