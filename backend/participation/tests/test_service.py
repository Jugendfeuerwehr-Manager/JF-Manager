from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from departments.models import Department
from members.models import Group
from participation import service
from participation.models import (
    ParticipationDefaults,
    Registration,
    RegistrationEvent,
    SessionParticipation,
)
from participation.service import ParticipationError, set_registration
from qualifications.models import Qualification, QualificationType

from .helpers import berlin, configure, make_member, make_session

User = get_user_model()
PORTAL = Registration.Source.PORTAL_PARENT
STAFF = Registration.Source.STAFF


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="A", code="a")
        cls.group = Group.objects.create(name="Rot", department=cls.dept)
        cls.user = User.objects.create_user("u")
        cls.session = make_session(cls.dept, day=date(2030, 3, 12), groups=[cls.group])  # starts 18:00 Berlin
        cls.mia = make_member(cls.dept, "Mia", cls.group)
        cls.ole = make_member(cls.dept, "Ole", cls.group)
        cls.start = berlin(2030, 3, 12, 18)
        cls.before = cls.start - timedelta(days=5)

    def put(self, member, target, *, source=PORTAL, now=None, session=None, **kw):
        return set_registration(
            (session or self.session).pk,
            member.pk,
            target,
            actor=self.user,
            source=source,
            now=now or self.before,
            **kw,
        )

    def refused(self, member, target, **kw):
        with self.assertRaises(ParticipationError) as ctx:
            self.put(member, target, **kw)
        return ctx.exception


class DeadlineTests(Base):
    def test_defaults_hierarchy(self):
        self.assertEqual(service.effective_defaults(self.dept.pk)["registration_offset_h"], 48)
        ParticipationDefaults.objects.create(department=None, registration_offset_h=72, cancellation_offset_h=4)
        self.assertEqual(service.effective_defaults(self.dept.pk)["registration_offset_h"], 72)
        ParticipationDefaults.objects.create(department=self.dept, registration_offset_h=24, cancellation_offset_h=1)
        self.assertEqual(service.effective_defaults(self.dept.pk)["registration_offset_h"], 24)
        self.assertEqual(service.effective_defaults(None)["registration_offset_h"], 72)

    def test_deadlines_from_defaults_and_session_override(self):
        p, persisted = service.participation_for(self.session)
        self.assertFalse(persisted)
        d = service.deadlines(self.session, p)
        self.assertEqual(d.registration_closes_at, self.start - timedelta(hours=48))
        self.assertEqual(d.cancellation_closes_at, self.start - timedelta(hours=2))
        custom = berlin(2030, 3, 11, 12)
        p = configure(self.session, cancellation_closes_at=custom)
        self.assertEqual(service.deadlines(self.session, p).cancellation_closes_at, custom)

    def test_deadline_is_capped_at_the_start(self):
        p = configure(self.session, cancellation_closes_at=self.start + timedelta(hours=3))
        self.assertEqual(service.deadlines(self.session, p).cancellation_closes_at, self.start)

    def test_offsets_are_real_hours_across_the_autumn_clock_change(self):
        # 2030-10-27 02:00 CEST -> 01:00 CET. Start Monday 06:00 CET; 48 h earlier is 07:00 CEST on Saturday.
        session = make_session(self.dept, day=date(2030, 10, 28), start=time(6), end=time(8))
        p, _ = service.participation_for(session)
        d = service.deadlines(session, p)
        self.assertEqual(d.registration_closes_at, berlin(2030, 10, 26, 7))
        self.assertEqual(d.registration_closes_at.utcoffset(), timedelta(hours=2))
        self.assertEqual(d.start.utcoffset(), timedelta(hours=1))

    def test_offsets_are_real_hours_across_the_spring_clock_change(self):
        # 2030-03-31 02:00 CET -> 03:00 CEST. Start Monday 06:00 CEST; 48 h earlier is 05:00 CET on Saturday.
        session = make_session(self.dept, day=date(2030, 4, 1), start=time(6), end=time(8))
        p, _ = service.participation_for(session)
        self.assertEqual(service.deadlines(session, p).registration_closes_at, berlin(2030, 3, 30, 5))

    def test_registration_exactly_at_the_deadline_still_works_one_second_later_not(self):
        configure(self.session, mode="opt_in")
        close = self.start - timedelta(hours=48)
        reg, changed, _ = self.put(self.mia, "registered", now=close)
        self.assertTrue(changed)
        self.assertEqual(reg.state, "registered")
        error = self.refused(self.ole, "registered", now=close + timedelta(seconds=1))
        self.assertEqual(error.code, "deadline_passed")

    def test_cancellation_has_its_own_later_deadline(self):
        configure(self.session, mode="opt_in")
        self.put(self.mia, "registered")
        now = self.start - timedelta(hours=10)  # registration closed, cancellation still open
        self.assertEqual(self.refused(self.ole, "registered", now=now).code, "deadline_passed")
        reg, _, plan = self.put(self.mia, "cancelled", now=now, reason_category="krankheit")
        self.assertEqual((reg.state, plan.late), ("cancelled", False))
        late = self.start - timedelta(hours=1)
        reg2 = self.refused(self.ole, "cancelled", now=late)
        self.assertEqual(
            (reg2.code, reg2.message), ("deadline_passed", "Abmeldung nur noch direkt bei der Dienstleitung.")
        )

    def test_opt_out_cancel_and_undo_follow_the_cancellation_deadline(self):
        now = self.start - timedelta(hours=10)  # opt_out is the hard default
        self.put(self.mia, "cancelled", now=now)
        reg, _, _ = self.put(self.mia, "registered", now=now)
        self.assertEqual(reg.state, "registered")
        self.assertEqual(
            self.refused(self.mia, "cancelled", now=self.start - timedelta(minutes=30)).code, "deadline_passed"
        )

    def test_frozen_from_the_start_even_for_staff(self):
        for source in (PORTAL, STAFF):
            with self.subTest(source=source):
                error = self.refused(self.mia, "cancelled", source=source, now=self.start)
                self.assertEqual(error.code, "deadline_passed")
                self.assertIn("begonnen", error.message)
        self.assertEqual(Registration.objects.count(), 0)

    def test_staff_after_deadline_is_flagged_late_and_portal_is_refused(self):
        now = self.start - timedelta(minutes=30)
        self.assertEqual(self.refused(self.mia, "cancelled", now=now).code, "deadline_passed")
        reg, _, plan = self.put(self.mia, "cancelled", source=STAFF, now=now)
        self.assertTrue(plan.late)
        self.assertTrue(reg.late)
        self.assertEqual(reg.source, "staff")
        # a later in-time change clears the flag
        reg, _, _ = self.put(self.mia, "registered", source=STAFF, now=self.before)
        self.assertFalse(reg.late)

    def test_registration_opens_at(self):
        configure(self.session, mode="opt_in", registration_opens_at=self.start - timedelta(days=4))
        self.assertEqual(self.refused(self.mia, "registered").code, "not_open")
        reg, _, _ = self.put(self.mia, "registered", source=STAFF)
        self.assertEqual(reg.state, "registered")  # staff are not bound to the opening
        reg, _, _ = self.put(self.ole, "registered", now=self.start - timedelta(days=3))
        self.assertEqual(reg.state, "registered")


class AvailabilityTests(Base):
    def test_only_published_sessions_are_open(self):
        for status in ("draft", "cancelled", "completed"):
            with self.subTest(status=status):
                session = make_session(self.dept, groups=[self.group], status=status, day=date(2030, 3, 13))
                self.assertEqual(self.refused(self.mia, "cancelled", session=session).code, "not_open")

    def test_portal_visible_false_blocks_portal_but_not_staff(self):
        configure(self.session, portal_visible=False)
        self.assertEqual(self.refused(self.mia, "cancelled").code, "not_open")
        reg, _, _ = self.put(self.mia, "cancelled", source=STAFF)
        self.assertEqual(reg.state, "cancelled")

    def test_person_outside_the_target_group_is_refused(self):
        other_group = Group.objects.create(name="Blau", department=self.dept)
        stranger = make_member(self.dept, "Fremd", other_group)
        self.assertEqual(self.refused(stranger, "cancelled").code, "not_target")

    def test_without_groups_the_whole_department_is_the_target(self):
        session = make_session(self.dept, day=date(2030, 3, 14))
        other = Department.objects.create(name="B", code="b")
        outsider = make_member(other, "Aussen")
        self.assertEqual(self.put(self.mia, "cancelled", session=session)[0].state, "cancelled")
        self.assertEqual(self.refused(outsider, "cancelled", session=session).code, "not_target")


class ModeAndHistoryTests(Base):
    def test_mode_forbidden(self):
        self.assertEqual(self.refused(self.mia, "applied").code, "mode_forbidden")
        configure(self.session, mode="opt_in")
        self.assertEqual(self.refused(self.mia, "withdrawn").code, "mode_forbidden")
        configure(self.session, mode="assignment")
        self.assertEqual(self.refused(self.mia, "registered").code, "mode_forbidden")

    def test_events_and_versions(self):
        reg, _, _ = self.put(self.mia, "cancelled", reason_category="urlaub", reason_note="Italien")
        self.assertEqual((reg.version, reg.reason_category, reg.reason_note), (1, "urlaub", "Italien"))
        reg, _, _ = self.put(self.mia, "registered")
        self.assertEqual((reg.version, reg.reason_category, reg.reason_note), (2, "", ""))
        events = list(RegistrationEvent.objects.filter(registration=reg).values_list("from_state", "to_state", "via"))
        self.assertEqual(events, [("", "cancelled", "portal_parent"), ("cancelled", "registered", "portal_parent")])

    def test_noop_writes_nothing(self):
        self.put(self.mia, "cancelled")
        _, changed, plan = self.put(self.mia, "cancelled")
        self.assertEqual((changed, plan.noop), (False, True))
        self.assertEqual(RegistrationEvent.objects.count(), 1)

    def test_participation_row_is_created_lazily_on_first_write(self):
        self.assertFalse(SessionParticipation.objects.exists())
        self.put(self.mia, "cancelled")
        self.assertEqual(SessionParticipation.objects.get().mode, "opt_out")

    def test_stale_version(self):
        self.put(self.mia, "cancelled")
        error = self.refused(self.mia, "registered", version=0)
        self.assertEqual((error.code, error.status), ("stale", 409))
        self.assertEqual(error.current, {"state": "cancelled", "version": 1})
        self.assertEqual(self.put(self.mia, "registered", version=1)[0].version, 2)

    def test_reason_validation(self):
        self.assertEqual(self.refused(self.mia, "cancelled", reason_category="x").status, 400)
        self.assertEqual(self.refused(self.mia, "cancelled", reason_note="x" * 201).status, 400)

    def test_mode_switch_keeps_cancellations(self):
        self.put(self.mia, "cancelled")
        configure(self.session, mode="opt_in")
        self.assertEqual(Registration.objects.get(member=self.mia).state, "cancelled")
        self.assertEqual(self.put(self.mia, "registered")[0].state, "registered")


class EligibilityTests(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.qtype = QualificationType.objects.create(name="Maschinist")
        cls.rule = {
            "v": 1,
            "match": "all",
            "rules": [{"kind": "qualification", "op": "has_any", "values": [cls.qtype.pk]}],
        }

    def test_registration_is_blocked_with_reasons(self):
        configure(self.session, mode="opt_in", eligibility=self.rule)
        error = self.refused(self.mia, "registered")
        self.assertEqual(error.code, "not_eligible")
        self.assertTrue(error.reasons)
        Qualification.objects.create(type=self.qtype, member=self.mia, date_acquired=date(2020, 1, 1))
        self.assertEqual(self.put(self.mia, "registered")[0].state, "registered")

    def test_staff_is_blocked_as_well_and_cancelling_is_always_possible(self):
        configure(self.session, mode="opt_in", eligibility=self.rule)
        self.assertEqual(self.refused(self.mia, "registered", source=STAFF).code, "not_eligible")
        self.assertEqual(self.put(self.mia, "cancelled")[0].state, "cancelled")

    def test_qualification_valid_on_the_day_counts(self):
        configure(self.session, mode="opt_in", eligibility=self.rule)
        Qualification.objects.create(
            type=self.qtype, member=self.mia, date_acquired=date(2020, 1, 1), date_expires=date(2030, 3, 11)
        )
        self.assertEqual(self.refused(self.mia, "registered").code, "not_eligible")

    def test_gender_reasons_are_neutralised_for_the_portal(self):
        reasons = ["Nur für Teilnehmende des Geschlechts weiblich", "Geburtsdatum ist nicht erfasst"]
        out = service.neutral_reasons(reasons)
        self.assertEqual(out, ["Dieser Dienst richtet sich an eine bestimmte Teilnehmendengruppe", reasons[1]])


class CapacityTests(Base):
    def setUp(self):
        configure(self.session, mode="opt_in", max_participants=2)
        self.m3 = make_member(self.dept, "Tom", self.group)
        self.m4 = make_member(self.dept, "Eva", self.group)

    def test_full_session_waitlists_in_order(self):
        self.put(self.mia, "registered", now=self.before)
        self.put(self.ole, "registered", now=self.before + timedelta(minutes=1))
        reg, _, plan = self.put(self.m3, "registered", now=self.before + timedelta(minutes=2))
        self.assertEqual((reg.state, plan.waitlisted), ("waitlisted", True))
        reg4, _, _ = self.put(self.m4, "registered", now=self.before + timedelta(minutes=3))
        self.assertEqual(service.waitlist_position(reg), 1)
        self.assertEqual(service.waitlist_position(reg4), 2)
        self.assertIsNone(service.waitlist_position(Registration.objects.get(member=self.mia)))

    def test_full_error_when_the_caller_does_not_accept_the_waitlist(self):
        self.put(self.mia, "registered")
        self.put(self.ole, "registered")
        self.assertEqual(self.refused(self.m3, "registered", accept_waitlist=False).code, "full")

    def test_cancelling_promotes_the_earliest_waitlisted_person(self):
        for i, m in enumerate((self.mia, self.ole, self.m3, self.m4)):
            self.put(m, "registered", now=self.before + timedelta(minutes=i))
        self.put(self.mia, "cancelled")
        states_ = {r.member.name: r.state for r in Registration.objects.select_related("member")}
        self.assertEqual(states_, {"Mia": "cancelled", "Ole": "registered", "Tom": "registered", "Eva": "waitlisted"})
        event = RegistrationEvent.objects.filter(registration__member=self.m3).order_by("pk").last()
        self.assertEqual(
            (event.from_state, event.to_state, event.via, event.actor), ("waitlisted", "registered", "system", None)
        )

    def test_promotion_skips_people_who_no_longer_qualify(self):
        qtype = QualificationType.objects.create(name="Atemschutz")
        rule = {"v": 1, "match": "all", "rules": [{"kind": "qualification", "op": "has_any", "values": [qtype.pk]}]}
        for m in (self.mia, self.ole, self.m3, self.m4):
            Qualification.objects.create(type=qtype, member=m, date_acquired=date(2020, 1, 1))
        configure(self.session, eligibility=rule)
        for i, m in enumerate((self.mia, self.ole, self.m3, self.m4)):
            self.put(m, "registered", now=self.before + timedelta(minutes=i))
        Qualification.objects.filter(member=self.m3).delete()  # first in line loses the qualification
        self.put(self.mia, "cancelled")
        self.assertEqual(Registration.objects.get(member=self.m3).state, "waitlisted")
        self.assertEqual(Registration.objects.get(member=self.m4).state, "registered")

    def test_manual_waitlist_does_not_promote(self):
        configure(self.session, waitlist_mode="manual")
        for i, m in enumerate((self.mia, self.ole, self.m3)):
            self.put(m, "registered", now=self.before + timedelta(minutes=i))
        self.put(self.mia, "cancelled")
        self.assertEqual(Registration.objects.get(member=self.m3).state, "waitlisted")

    def test_waitlist_place_can_be_given_back(self):
        for m in (self.mia, self.ole, self.m3):
            self.put(m, "registered")
        self.assertEqual(self.put(self.m3, "cancelled")[0].state, "cancelled")
        self.assertEqual(Registration.objects.filter(state="registered").count(), 2)

    def test_opt_out_ignores_the_maximum(self):
        configure(self.session, mode="opt_out", max_participants=1)
        for m in (self.mia, self.ole):
            self.put(m, "cancelled")
            self.assertEqual(self.put(m, "registered")[0].state, "registered")

    def test_no_maximum_means_no_waitlist(self):
        configure(self.session, max_participants=None)
        for m in (self.mia, self.ole, self.m3, self.m4):
            self.assertEqual(self.put(m, "registered")[0].state, "registered")


class AssignmentModeTests(Base):
    def test_apply_withdraw_and_cancel_after_assignment(self):
        configure(self.session, mode="assignment")
        self.assertEqual(self.put(self.mia, "applied")[0].state, "applied")
        self.assertEqual(self.put(self.mia, "withdrawn")[0].state, "cancelled")
        self.put(self.mia, "applied")
        Registration.objects.filter(member=self.mia).update(state="assigned")
        self.assertEqual(self.put(self.mia, "cancelled")[0].state, "cancelled")
        self.assertEqual(self.refused(self.ole, "withdrawn").code, "invalid_transition")


class AbsenceTests(Base):
    def setUp(self):
        self.now = berlin(2030, 3, 1, 12)
        self.s1 = make_session(self.dept, day=date(2030, 3, 5), groups=[self.group], title="S1")
        self.s2 = make_session(self.dept, day=date(2030, 3, 7), groups=[self.group], title="S2")
        self.s3 = make_session(self.dept, day=date(2030, 3, 9), groups=[self.group], title="S3", status="draft")
        self.s_past = make_session(self.dept, day=date(2030, 2, 20), groups=[self.group], title="alt")
        self.s_other = make_session(
            self.dept, day=date(2030, 3, 6), groups=[Group.objects.create(name="X", department=self.dept)]
        )
        self.s_hidden = make_session(self.dept, day=date(2030, 3, 8), groups=[self.group], title="hidden")
        configure(self.s_hidden, portal_visible=False)

    def preview(self, member=None, **kw):
        return service.preview_absence(
            member or self.mia, date(2030, 3, 1), date(2030, 3, 12), source=PORTAL, now=kw.pop("now", self.now)
        )

    def test_preview_lists_published_visible_target_sessions(self):
        titles = [(i["session"].title, i["action"]) for i in self.preview()]
        self.assertEqual(titles, [("S1", "cancel"), ("S2", "cancel"), ("Übung", "cancel")])  # 12 March session of Base

    def test_deadline_passed_sessions_are_skipped_with_reason(self):
        now = berlin(2030, 3, 5, 17, 30)  # S1 starts 18:00, cancellation closes 16:00
        items = {i["session"].title: i for i in self.preview(now=now)}
        self.assertEqual(items["S1"]["action"], "skip")
        self.assertEqual(items["S1"]["skip"]["code"], "deadline_passed")
        self.assertEqual(items["S2"]["action"], "cancel")

    def test_execute_cancels_and_reports_skips(self):
        self.put(self.mia, "cancelled", session=self.s2, now=self.now)
        cancelled, skipped = service.execute_absence(
            self.mia,
            date(2030, 3, 1),
            date(2030, 3, 7),
            actor=self.user,
            source=PORTAL,
            reason_category="urlaub",
            reason_note="Ferien",
            now=self.now,
        )
        self.assertEqual([s.title for s in cancelled], ["S1"])
        self.assertEqual([(s.title, k["code"]) for s, k in skipped], [("S2", "already_cancelled")])
        reg = Registration.objects.get(member=self.mia, session=self.s1)
        self.assertEqual((reg.state, reg.reason_category, reg.reason_note), ("cancelled", "urlaub", "Ferien"))

    def test_execute_after_deadline_skips(self):
        cancelled, skipped = service.execute_absence(
            self.mia, date(2030, 3, 5), date(2030, 3, 5), actor=self.user, source=PORTAL, now=berlin(2030, 3, 5, 17)
        )
        self.assertEqual((cancelled, [k["code"] for _, k in skipped]), ([], ["deadline_passed"]))

    def test_range_validation(self):
        with self.assertRaises(ParticipationError):
            service.preview_absence(self.mia, date(2030, 3, 9), date(2030, 3, 1), source=PORTAL)
        with self.assertRaises(ParticipationError):
            service.preview_absence(self.mia, date(2030, 1, 1), date(2032, 1, 1), source=PORTAL)

    def test_person_without_group_matches_department_sessions_only(self):
        lone = make_member(self.dept, "Solo")
        titles = [
            i["session"].title
            for i in service.preview_absence(lone, date(2030, 3, 1), date(2030, 3, 31), source=PORTAL, now=self.now)
        ]
        self.assertEqual(titles, [])  # every session of the department has groups
        make_session(self.dept, day=date(2030, 3, 20), title="offen")
        titles = [
            i["session"].title
            for i in service.preview_absence(lone, date(2030, 3, 1), date(2030, 3, 31), source=PORTAL, now=self.now)
        ]
        self.assertEqual(titles, ["offen"])
