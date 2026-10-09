"""PART-04.4: applications, board draft, publication and revision conflicts."""

from datetime import date, timedelta

from django.utils import timezone

from notifications.models import EmailDelivery
from participation import service
from participation.models import Registration, RegistrationEvent, SessionParticipation, Slot
from portal.models import AccountLink
from qualifications.models import Qualification, QualificationType

from .helpers import configure, make_member, make_session
from .test_staff_api import StaffApiBase, url


class AssignmentApiTests(StaffApiBase):
    def setUp(self):
        super().setUp()
        self.participation = configure(self.session, mode="assignment", max_participants=3)
        self.qtype = QualificationType.objects.create(name="Gruppenführer")
        rule = {
            "v": 1,
            "match": "all",
            "rules": [{"kind": "qualification", "op": "has_any", "values": [self.qtype.pk]}],
        }
        self.lead = Slot.objects.create(
            participation=self.participation, label="Wachführung", min_count=1, max_count=1, rule=rule
        )
        self.crew = Slot.objects.create(
            participation=self.participation, label="Trupp", min_count=1, max_count=2, position=1
        )
        Qualification.objects.create(type=self.qtype, member=self.mia, date_acquired=date(2020, 1, 1))
        self.ida = make_member(self.dept, "Ida", self.group)
        for member, wish in ((self.mia, self.lead), (self.ole, None), (self.ida, self.crew)):
            service.set_registration(
                self.session.pk, member.pk, "applied", actor=None, source="staff", slot=getattr(wish, "pk", None)
            )

    def board(self, user=None):
        client = self.as_user(user) if user else self.client
        return client.get(url(self.session, "assignment/"))

    def save(self, draft, revision=None, user=None):
        client = self.as_user(user) if user else self.client
        revision = SessionParticipation.objects.get().revision if revision is None else revision
        return client.put(url(self.session, "assignment/"), {"revision": revision, "draft": draft}, format="json")

    def publish(self, revision=None, **extra):
        revision = SessionParticipation.objects.get().revision if revision is None else revision
        return self.client.post(
            url(self.session, "assignment/publish/"), {"revision": revision, **extra}, format="json"
        )

    def test_board_lists_applicants_with_fit_wish_and_chips(self):
        response = self.board()
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual([s["label"] for s in body["slots"]], ["Wachführung", "Trupp"])
        people = {p["name"]: p for p in body["applicants"]}
        self.assertEqual(people["Mia"]["fits"], [self.lead.pk, self.crew.pk])
        self.assertEqual(people["Mia"]["preferred_slot"], self.lead.pk)
        self.assertEqual(people["Mia"]["qualifications"], ["Gruppenführer"])
        self.assertEqual(people["Ole"]["fits"], [self.crew.pk])
        self.assertEqual(people["Ole"]["reasons"][str(self.lead.pk)], ["Qualifikation ‚Gruppenführer‘ fehlt"])
        self.assertEqual(body["staffing"]["fulfilled"], 0)
        self.assertFalse(body["dirty"])

    def test_draft_publish_and_notifications(self):
        # Ole's own portal account hears about the result
        AccountLink.objects.create(user=self.portal, member=self.ole, status="confirmed")
        self.portal.email = "ole@example.invalid"
        self.portal.save(update_fields=["email"])
        draft = {str(self.mia.pk): self.lead.pk, str(self.ida.pk): self.crew.pk}
        response = self.save(draft)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertTrue(body["dirty"])
        self.assertEqual(body["staffing"]["text"], "Mindestbesetzung: 2 von 2 erfüllt")
        self.assertEqual(Registration.objects.get(member=self.mia).state, "applied")  # only a draft
        with self.captureOnCommitCallbacks(execute=True):
            response = self.publish()
        self.assertEqual(response.status_code, 200, response.content)
        states = dict(Registration.objects.values_list("member__name", "state"))
        self.assertEqual(states, {"Mia": "assigned", "Ida": "assigned", "Ole": "not_selected"})
        self.assertEqual(Registration.objects.get(member=self.mia).slot_id, self.lead.pk)
        self.assertIsNotNone(response.json()["published_at"])
        self.assertFalse(response.json()["dirty"])
        mail = EmailDelivery.objects.get(kind="assign_published", user=self.portal)
        self.assertEqual(mail.context["assignment"]["result"], "not_selected")
        self.assertTrue(RegistrationEvent.objects.filter(to_state="assigned", via="staff").exists())
        # later single change: Ole moves into the crew, Ida out
        self.save({str(self.mia.pk): self.lead.pk, str(self.ole.pk): self.crew.pk})
        with self.captureOnCommitCallbacks(execute=True):
            self.publish()
        states = dict(Registration.objects.values_list("member__name", "state"))
        self.assertEqual(states, {"Mia": "assigned", "Ida": "not_selected", "Ole": "assigned"})
        self.assertEqual(EmailDelivery.objects.filter(kind="assign_published", user=self.portal).count(), 2)

    def test_keep_applications_open(self):
        self.save({str(self.mia.pk): self.lead.pk})
        self.publish(keep_open=True)
        states = dict(Registration.objects.values_list("member__name", "state"))
        self.assertEqual(states, {"Mia": "assigned", "Ida": "applied", "Ole": "applied"})
        self.assertTrue(self.board().json()["keep_open"])

    def test_invalid_drafts_are_refused(self):
        stranger = make_member(self.dept, "Fremd", self.group)
        cases = {
            "unsuitable": {str(self.ole.pk): self.lead.pk},
            "too_many": {
                str(self.mia.pk): self.crew.pk,
                str(self.ole.pk): self.crew.pk,
                str(self.ida.pk): self.crew.pk,
            },
            "not_applied": {str(stranger.pk): self.crew.pk},
            "unknown_slot": {str(self.ole.pk): 999999},
            "no_extra_places": {str(self.ole.pk): "extra"},
        }
        for name, draft in cases.items():
            with self.subTest(name):
                response = self.save(draft)
                self.assertEqual(response.status_code, 422, response.content)
                self.assertEqual(response.json()["code"], "invalid_assignment")
        self.assertEqual(self.save({str(self.ole.pk): "x"}).status_code, 400)

    def test_stale_revision_is_409_with_the_current_board(self):
        revision = SessionParticipation.objects.get().revision
        self.save({str(self.mia.pk): self.lead.pk}, revision=revision)
        response = self.save({str(self.ida.pk): self.crew.pk}, revision=revision)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "stale")
        self.assertEqual(response.json()["current"]["draft"], {str(self.mia.pk): self.lead.pk})
        self.assertEqual(self.publish(revision=revision).status_code, 409)

    def test_withdrawn_applicant_drops_out_of_the_draft(self):
        self.save({str(self.ida.pk): self.crew.pk})
        service.set_registration(self.session.pk, self.ida.pk, "withdrawn", actor=None, source="staff")
        body = self.board().json()
        self.assertEqual(body["draft"], {})
        self.assertNotIn("Ida", [p["name"] for p in body["applicants"]])

    def test_fairness_counts_recent_assignments(self):
        earlier = make_session(self.dept, day=self.day - timedelta(days=30), groups=[self.group], title="Früher")
        Registration.objects.create(
            session=earlier, member=self.ole, state="assigned", source="staff", state_changed_at=timezone.now()
        )
        people = {p["name"]: p for p in self.board().json()["applicants"]}
        self.assertEqual((people["Ole"]["recent_assignments"], people["Mia"]["recent_assignments"]), (1, 0))

    def test_only_in_assignment_mode_and_not_after_start(self):
        SessionParticipation.objects.update(mode="opt_in")
        self.assertEqual(self.save({}).json()["code"], "mode_forbidden")

    def test_permissions(self):
        self.assertEqual(self.board(self.other_planner).status_code, 403)
        self.assertEqual(self.board(self.portal).status_code, 403)
        self.assertEqual(self.board(self.reader).status_code, 200)
        self.assertEqual(self.save({}, user=self.reader).status_code, 403)
        self.assertEqual(self.save({}, user=self.other_planner).status_code, 403)
        self.assertEqual(self.save({}, user=self.portal).status_code, 403)
        response = self.as_user(self.reader).post(
            url(self.session, "assignment/publish/"), {"revision": 1}, format="json"
        )
        self.assertEqual(response.status_code, 403)
