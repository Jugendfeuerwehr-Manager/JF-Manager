from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department
from members.models import Group, Member, Parent
from participation import service
from participation.models import Registration
from participation.signals import session_published
from portal.models import AccountLink
from qualifications.models import QualificationType
from training.models import TrainingSession

from .helpers import configure, future_day, make_member, make_session

User = get_user_model()
LIST = "/api/v1/portal/sessions/"


def put_url(session, member):
    return f"/api/v1/portal/sessions/{session.pk}/registrations/{member.pk}/"


def years_ago(years, days=0):
    today = timezone.localdate()
    return date(today.year - years, today.month, min(today.day, 28)) - timedelta(days=days)


class PortalBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="A", code="a")
        cls.group = Group.objects.create(name="Rot", department=cls.dept)
        cls.parent_user = User.objects.create_user("eltern", account_kind="portal")
        cls.parent = Parent.objects.create(name="Eva", lastname="Test")
        cls.mia = make_member(cls.dept, "Mia", cls.group, birthday=years_ago(12))
        cls.adult = make_member(cls.dept, "Tom", cls.group, birthday=years_ago(18, days=1))
        cls.parent.children.add(cls.mia, cls.adult)
        AccountLink.objects.create(user=cls.parent_user, parent=cls.parent, status="confirmed")
        cls.other_child = make_member(cls.dept, "Fremd", cls.group, birthday=years_ago(11))
        cls.member_user = User.objects.create_user("ole-konto", account_kind="portal")
        cls.ole = make_member(cls.dept, "Ole", cls.group, birthday=years_ago(16))
        AccountLink.objects.create(user=cls.member_user, member=cls.ole, status="confirmed")
        cls.staff = User.objects.create_superuser("admin")
        cls.session = make_session(cls.dept, day=future_day(20), groups=[cls.group], location="Gerätehaus")

    def setUp(self):
        cache.clear()
        self.client = self.login(self.parent_user)

    def login(self, user):
        client = APIClient()
        client.force_login(user)
        return client

    def body(self, target, **kw):
        return {"target": target, **kw}


class ListTests(PortalBase):
    def test_lists_sessions_for_the_child(self):
        response = self.client.get(LIST, {"person": self.mia.pk})
        self.assertEqual(response.status_code, 200, response.content)
        [item] = response.json()["sessions"]
        self.assertEqual(item["id"], self.session.pk)
        self.assertEqual((item["title"], item["place"], item["mode"]), ("Übung", "Gerätehaus", "opt_out"))
        self.assertEqual((item["state"], item["may_cancel"], item["may_register"]), ("expected", True, False))
        self.assertEqual(item["start_time"], "18:00:00")
        self.assertIsNone(item["free_places"])
        self.assertTrue(item["deadlines"]["cancellation_closes_at"])

    def test_foreign_and_adult_persons_are_404(self):
        for person in (self.other_child.pk, self.adult.pk, self.ole.pk, 999999):
            with self.subTest(person=person):
                self.assertEqual(self.client.get(LIST, {"person": person}).status_code, 404)
                response = self.client.put(
                    put_url(self.session, Member(pk=person)), self.body("cancelled"), format="json"
                )
                self.assertEqual(response.status_code, 404)
        self.assertFalse(Registration.objects.exists())

    def test_person_is_required(self):
        self.assertEqual(self.client.get(LIST).status_code, 400)
        self.assertEqual(self.client.get(LIST, {"person": "x"}).status_code, 400)

    def test_member_account_sees_itself_only(self):
        client = self.login(self.member_user)
        self.assertEqual(client.get(LIST, {"person": self.ole.pk}).status_code, 200)
        self.assertEqual(client.get(LIST, {"person": self.mia.pk}).status_code, 404)

    def test_staff_accounts_are_refused(self):
        client = self.login(self.staff)
        self.assertEqual(client.get(LIST, {"person": self.mia.pk}).status_code, 403)
        self.assertEqual(
            client.put(put_url(self.session, self.mia), self.body("cancelled"), format="json").status_code, 403
        )
        self.assertEqual(client.post("/api/v1/portal/absences/preview/", {}, format="json").status_code, 403)
        self.assertIn(APIClient().get(LIST, {"person": self.mia.pk}).status_code, (401, 403))

    def test_hidden_draft_past_and_foreign_group_sessions_are_not_listed(self):
        make_session(self.dept, day=future_day(21), groups=[self.group], status="draft")
        hidden = make_session(self.dept, day=future_day(22), groups=[self.group])
        configure(hidden, portal_visible=False)
        make_session(self.dept, day=future_day(23), groups=[Group.objects.create(name="Blau", department=self.dept)])
        make_session(self.dept, day=date(2020, 1, 1), groups=[self.group])
        beyond = make_session(self.dept, day=future_day(200), groups=[self.group])
        items = self.client.get(LIST, {"person": self.mia.pk}).json()["sessions"]
        self.assertEqual([i["id"] for i in items], [self.session.pk])
        far = self.client.get(LIST, {"person": self.mia.pk, "to": str(future_day(300))}).json()["sessions"]
        self.assertEqual([i["id"] for i in far], [self.session.pk, beyond.pk])

    def test_cancelled_sessions_are_shown_frozen(self):
        make_session(self.dept, day=future_day(21), groups=[self.group], status="cancelled", title="Abgesagt")
        items = self.client.get(LIST, {"person": self.mia.pk}).json()["sessions"]
        cancelled = next(i for i in items if i["title"] == "Abgesagt")
        self.assertEqual(
            (cancelled["session_status"], cancelled["may_cancel"], cancelled["may_register"]),
            ("cancelled", False, False),
        )
        self.assertEqual(cancelled["cancel_blocked"]["code"], "not_open")
        response = self.client.put(
            put_url(TrainingSession.objects.get(title="Abgesagt"), self.mia), self.body("cancelled"), format="json"
        )
        self.assertEqual((response.status_code, response.json()["code"]), (422, "not_open"))

    def test_free_places_are_counts_without_names(self):
        configure(self.session, mode="opt_in", max_participants=2, public_note="Bitte pünktlich")
        service.set_registration(self.session.pk, self.other_child.pk, "registered", actor=None, source="staff")
        response = self.client.get(LIST, {"person": self.mia.pk})
        [item] = response.json()["sessions"]
        self.assertEqual((item["limited"], item["free_places"], item["state"]), (True, 1, "no_response"))
        self.assertIsNotNone(item["max_participants"])
        self.assertEqual(item["public_note"], "Bitte pünktlich")
        self.assertNotIn("Fremd", response.content.decode())
        self.assertNotIn(str(self.other_child.pk) + ",", response.content.decode())

    def test_waitlist_position_is_own_only(self):
        configure(self.session, mode="opt_in", max_participants=1)
        for member in (self.other_child, self.ole, self.mia):
            service.set_registration(self.session.pk, member.pk, "registered", actor=None, source="staff")
        [item] = self.client.get(LIST, {"person": self.mia.pk}).json()["sessions"]
        self.assertEqual((item["state"], item["waitlist_position"], item["free_places"]), ("waitlisted", 2, 0))

    def test_eligibility_reasons_for_this_person_only_with_neutral_gender_notice(self):
        qtype = QualificationType.objects.create(name="Maschinist")
        rule = {
            "v": 1,
            "match": "all",
            "rules": [
                {"kind": "qualification", "op": "has_any", "values": [qtype.pk]},
                {"kind": "gender", "op": "in", "values": ["female"]},
            ],
        }
        configure(self.session, mode="opt_in", eligibility=rule)
        self.mia.gender = "male"
        self.mia.save()
        response = self.client.get(LIST, {"person": self.mia.pk})
        [item] = response.json()["sessions"]
        self.assertFalse(item["eligibility"]["ok"])
        self.assertFalse(item["may_register"])
        text = response.content.decode()
        self.assertIn("bestimmte Teilnehmendengruppe", text)
        self.assertNotIn("Geschlecht", text)
        self.assertEqual(item["register_blocked"]["code"], "not_eligible")
        self.assertEqual(item["eligibility"]["audience_notice"], item["eligibility"]["reasons"][-1])

    def test_response_never_contains_notes_or_events(self):
        configure(self.session, mode="opt_in")
        self.client.put(
            put_url(self.session, self.mia),
            self.body("cancelled", reason_category="krankheit", reason_note="GEHEIMNOTIZ"),
            format="json",
        )
        text = (
            self.client.get(LIST, {"person": self.mia.pk}).content.decode()
            + self.client.put(put_url(self.session, self.mia), self.body("registered"), format="json").content.decode()
        )
        self.assertNotIn("GEHEIMNOTIZ", text)
        self.assertNotIn("reason_note", text)
        self.assertNotIn("events", text)


class RegisterTests(PortalBase):
    def test_parent_cancels_and_undoes_in_opt_out(self):
        path = put_url(self.session, self.mia)
        response = self.client.put(
            path, self.body("cancelled", reason_category="urlaub", reason_note="Italien", version=0), format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        item = response.json()
        self.assertEqual((item["state"], item["reason_category"], item["version"]), ("cancelled", "urlaub", 1))
        reg = Registration.objects.get()
        self.assertEqual((reg.source, reg.created_by, reg.reason_note), ("portal_parent", self.parent_user, "Italien"))
        response = self.client.put(path, self.body("registered", version=1), format="json")
        self.assertEqual((response.json()["state"], response.json()["version"]), ("registered", 2))
        self.assertEqual(Registration.objects.get().reason_note, "")

    def test_member_account_uses_its_own_source(self):
        client = self.login(self.member_user)
        client.put(put_url(self.session, self.ole), self.body("cancelled"), format="json")
        self.assertEqual(Registration.objects.get().source, "portal_member")

    def test_stale_version_is_409(self):
        path = put_url(self.session, self.mia)
        self.client.put(path, self.body("cancelled"), format="json")
        response = self.client.put(path, self.body("registered", version=0), format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (409, "stale"))

    def test_error_contract(self):
        path = put_url(self.session, self.mia)
        response = self.client.put(path, self.body("applied"), format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (422, "mode_forbidden"))
        self.assertEqual(self.client.put(path, self.body("bogus"), format="json").status_code, 400)
        self.assertEqual(
            self.client.put(path, self.body("cancelled", reason_category="x"), format="json").status_code, 400
        )
        self.assertEqual(
            self.client.put(path, self.body("cancelled", reason_note="x" * 201), format="json").status_code, 400
        )
        soon = make_session(self.dept, day=future_day(1), groups=[self.group])
        configure(soon, cancellation_closes_at=timezone.now() - timedelta(hours=1))
        response = self.client.put(put_url(soon, self.mia), self.body("cancelled"), format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (422, "deadline_passed"))
        self.assertIn("Dienstleitung", response.json()["detail"])

    def test_not_eligible_and_full_codes(self):
        qtype = QualificationType.objects.create(name="Maschinist")
        rule = {"v": 1, "match": "all", "rules": [{"kind": "qualification", "op": "has_any", "values": [qtype.pk]}]}
        configure(self.session, mode="opt_in", eligibility=rule)
        response = self.client.put(put_url(self.session, self.mia), self.body("registered"), format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (422, "not_eligible"))
        self.assertTrue(response.json()["reasons"])
        configure(self.session, eligibility={}, max_participants=1)
        service.set_registration(self.session.pk, self.ole.pk, "registered", actor=None, source="staff")
        response = self.client.put(
            put_url(self.session, self.mia), self.body("registered", accept_waitlist=False), format="json"
        )
        self.assertEqual((response.status_code, response.json()["code"]), (422, "full"))
        response = self.client.put(put_url(self.session, self.mia), self.body("registered"), format="json")
        self.assertEqual(
            (response.status_code, response.json()["state"], response.json()["waitlist_position"]),
            (200, "waitlisted", 1),
        )

    def test_session_of_another_group_or_hidden_is_404(self):
        blue = make_session(
            self.dept, day=future_day(30), groups=[Group.objects.create(name="Blau", department=self.dept)]
        )
        self.assertEqual(
            self.client.put(put_url(blue, self.mia), self.body("cancelled"), format="json").status_code, 404
        )
        configure(self.session, portal_visible=False)
        self.assertEqual(
            self.client.put(put_url(self.session, self.mia), self.body("cancelled"), format="json").status_code, 404
        )
        draft = make_session(self.dept, day=future_day(31), groups=[self.group], status="draft")
        self.assertEqual(
            self.client.put(put_url(draft, self.mia), self.body("cancelled"), format="json").status_code, 404
        )

    def test_write_rate_limit(self):
        path = put_url(self.session, self.mia)
        codes = [self.client.put(path, self.body("cancelled"), format="json").status_code for _ in range(31)]
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[30], 429)
        self.assertEqual(self.client.get(LIST, {"person": self.mia.pk}).status_code, 200)  # reads are free
        self.assertEqual(
            self.login(self.member_user)
            .put(put_url(self.session, self.ole), self.body("cancelled"), format="json")
            .status_code,
            200,
        )


class AbsenceTests(PortalBase):
    def setUp(self):
        super().setUp()
        self.s2 = make_session(self.dept, day=future_day(22), groups=[self.group], title="Zwei")
        self.s3 = make_session(self.dept, day=future_day(40), groups=[self.group], title="Drei")
        self.payload = {
            "person": self.mia.pk,
            "from": str(future_day(19)),
            "to": str(future_day(30)),
            "reason_category": "urlaub",
            "reason_note": "Ferien",
        }

    def test_preview_then_execute(self):
        response = self.client.post("/api/v1/portal/absences/preview/", self.payload, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual([s["title"] for s in body["sessions"]], ["Übung", "Zwei"])
        self.assertEqual((body["will_cancel"], body["skipped"]), (2, 0))
        self.assertFalse(Registration.objects.exists())
        response = self.client.post("/api/v1/portal/absences/", self.payload, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([s["title"] for s in response.json()["cancelled"]], ["Übung", "Zwei"])
        self.assertEqual(set(Registration.objects.values_list("state", "reason_category")), {("cancelled", "urlaub")})
        self.assertEqual(Registration.objects.count(), 2)
        again = self.client.post("/api/v1/portal/absences/preview/", self.payload, format="json").json()
        self.assertEqual({s["skip"]["code"] for s in again["sessions"]}, {"already_cancelled"})

    def test_deadline_passed_sessions_are_skipped(self):
        soon = make_session(self.dept, day=future_day(1), groups=[self.group], title="Morgen")
        configure(soon, cancellation_closes_at=timezone.now() - timedelta(minutes=5))
        payload = {**self.payload, "from": str(future_day(0)), "to": str(future_day(2))}
        body = self.client.post("/api/v1/portal/absences/", payload, format="json").json()
        self.assertEqual(body["cancelled"], [])
        self.assertEqual([(s["title"], s["code"]) for s in body["skipped"]], [("Morgen", "deadline_passed")])

    def test_foreign_person_and_bad_ranges(self):
        for person in (self.other_child.pk, self.adult.pk):
            payload = {**self.payload, "person": person}
            self.assertEqual(
                self.client.post("/api/v1/portal/absences/preview/", payload, format="json").status_code, 404
            )
            self.assertEqual(self.client.post("/api/v1/portal/absences/", payload, format="json").status_code, 404)
        reversed_range = {**self.payload, "from": self.payload["to"], "to": self.payload["from"]}
        self.assertEqual(
            self.client.post("/api/v1/portal/absences/preview/", reversed_range, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.post("/api/v1/portal/absences/preview/", {"person": self.mia.pk}, format="json").status_code,
            400,
        )
        self.assertFalse(Registration.objects.exists())


class StaffBoundaryTests(PortalBase):
    def test_portal_accounts_are_refused_by_the_staff_api(self):
        base = f"/api/v1/participation/sessions/{self.session.pk}/"
        for client in (self.client, self.login(self.member_user)):
            self.assertEqual(client.get(base + "config/").status_code, 403)
            self.assertEqual(client.get(base + "registrations/").status_code, 403)
            self.assertEqual(
                client.put(base + f"registrations/{self.mia.pk}/", {"target": "cancelled"}, format="json").status_code,
                403,
            )


class SessionPublishedSignalTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="A", code="a")
        self.received = []

        def handler(sender, session, **kwargs):
            self.received.append(session.pk)

        self.handler = handler
        session_published.connect(handler)
        self.addCleanup(session_published.disconnect, handler)

    def test_sent_once_when_a_session_becomes_published(self):
        with self.captureOnCommitCallbacks(execute=True):
            session = make_session(self.dept, day=future_day(10), status="draft")
        self.assertEqual(self.received, [])
        with self.captureOnCommitCallbacks(execute=True):
            session.status = "published"
            session.save()
        self.assertEqual(self.received, [session.pk])
        with self.captureOnCommitCallbacks(execute=True):
            session.title = "Neu"
            session.save()
        self.assertEqual(self.received, [session.pk])

    def test_created_as_published_counts(self):
        with self.captureOnCommitCallbacks(execute=True):
            session = make_session(self.dept, day=future_day(10))
        self.assertEqual(self.received, [session.pk])

    def test_string_dates_do_not_break_saving(self):
        session = TrainingSession(
            title="Roh", date="2030-01-01", start_time="18:00", end_time="19:00", status="published"
        )
        session.save()
        self.assertEqual(self.received, [])

    def test_not_for_past_hidden_or_cancelled_sessions(self):
        with self.captureOnCommitCallbacks(execute=True):
            make_session(self.dept, day=date(2020, 1, 1))
            hidden = make_session(self.dept, day=future_day(5), status="draft")
            configure(hidden, portal_visible=False)
            hidden.status = "published"
            hidden.save()
            make_session(self.dept, day=future_day(6), status="cancelled")
        self.assertEqual(self.received, [])


class PurgeCommandTests(PortalBase):
    def test_notes_are_deleted_90_days_after_the_service(self):
        old = make_session(self.dept, day=timezone.localdate() - timedelta(days=91), groups=[self.group])
        edge = make_session(self.dept, day=timezone.localdate() - timedelta(days=90), groups=[self.group])
        now = timezone.now()
        for session in (old, edge, self.session):
            Registration.objects.create(
                session=session,
                member=self.mia,
                state="cancelled",
                source="staff",
                state_changed_at=now,
                reason_category="krankheit",
                reason_note="Kurztext",
            )
        Registration.objects.create(
            session=old, member=self.ole, state="registered", source="staff", state_changed_at=now
        )
        out = StringIO()
        call_command("purge_registration_notes", "--dry-run", stdout=out)
        self.assertIn("1 Kurztexte", out.getvalue())
        self.assertEqual(Registration.objects.exclude(reason_note="").count(), 3)
        call_command("purge_registration_notes", stdout=out)
        notes = {r.session_id: (r.reason_note, r.reason_category) for r in Registration.objects.filter(member=self.mia)}
        self.assertEqual(notes[old.pk], ("", "krankheit"))  # the category stays, only the free text goes
        self.assertEqual(notes[edge.pk][0], "Kurztext")
        self.assertEqual(notes[self.session.pk][0], "Kurztext")
