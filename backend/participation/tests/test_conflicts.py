from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from departments.models import Department
from participation.conflicts import recheck
from participation.models import Registration, SessionParticipation
from participation.signals import eligibility_conflict
from portal.models import AccountLink
from qualifications.models import Qualification, SpecialTask

from .helpers import configure, make_member, make_session
from .test_rules import RuleFixtureMixin, rule

DAY = date(2030, 3, 12)


class ConflictTests(RuleFixtureMixin, TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Jugend", code="jf")
        self.session = make_session(self.dept, day=DAY)
        self.mia = make_member(self.dept, "Mia", birthday=date(2014, 5, 1))
        self.qrule = rule({"kind": "qualification", "op": "has_any", "values": [self.maschinist.pk]})
        configure(self.session, eligibility=self.qrule)
        self.qual = Qualification.objects.create(
            type=self.maschinist, member=self.mia, date_acquired=date(2020, 1, 1), date_expires=date(2031, 1, 1)
        )
        self.reg = self.register(self.mia)
        self.events = []
        eligibility_conflict.connect(self.listen, weak=False)
        self.addCleanup(eligibility_conflict.disconnect, self.listen)

    def listen(self, sender, session, registration_ids, **kw):
        self.events.append((session.pk, list(registration_ids)))

    def register(self, member, state="registered", session=None):
        return Registration.objects.create(
            session=session or self.session,
            member=member,
            state=state,
            source="staff",
            state_changed_at=timezone.now(),
        )

    def refresh(self, reg=None):
        reg = reg or self.reg
        reg.refresh_from_db()
        return reg

    def test_expiry_before_session_date_sets_conflict_and_renewal_clears(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.qual.date_expires = date(2030, 3, 1)
            self.qual.save()
        reg = self.refresh()
        self.assertTrue(reg.conflict)
        self.assertEqual(reg.conflict_reasons, ["Qualifikation ‚Maschinist‘: Gültig nur bis 01.03.2030"])
        self.assertEqual(reg.state, "registered")
        with self.captureOnCommitCallbacks(execute=True):
            self.qual.date_expires = date(2032, 1, 1)
            self.qual.save()
        reg = self.refresh()
        self.assertFalse(reg.conflict)
        self.assertEqual(reg.conflict_reasons, [])

    def test_deleted_qualification_and_special_task(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.qual.delete()
        self.assertTrue(self.refresh().conflict)
        configure(self.session, eligibility=rule({"kind": "special_task", "op": "has_any", "values": [self.task.pk]}))
        task = SpecialTask.objects.create(task=self.task, member=self.mia, start_date=date(2020, 1, 1))
        with self.captureOnCommitCallbacks(execute=True):
            task.save()
        self.assertFalse(self.refresh().conflict)
        with self.captureOnCommitCallbacks(execute=True):
            task.delete()
        self.assertTrue(self.refresh().conflict)

    def test_account_link_qualification(self):
        user = get_user_model().objects.create_user(username="mia", password="x")
        link = AccountLink.objects.create(user=user, member=self.mia, status=AccountLink.Status.CONFIRMED)
        self.qual.delete()
        Qualification.objects.create(type=self.maschinist, user=user, date_acquired=date(2020, 1, 1))
        recheck()
        self.assertFalse(self.refresh().conflict)
        with self.captureOnCommitCallbacks(execute=True):
            Qualification.objects.filter(user=user).update(date_expires=date(2030, 1, 1))
            link.delete()  # the link vanishes: the account's qualification no longer counts
        self.assertTrue(self.refresh().conflict)
        with self.captureOnCommitCallbacks(execute=True):
            AccountLink.objects.create(user=user, member=self.mia, status=AccountLink.Status.CONFIRMED)
        self.assertTrue(self.refresh().conflict)  # expired
        with self.captureOnCommitCallbacks(execute=True):
            Qualification.objects.filter(user=user).first().save()
            Qualification.objects.filter(user=user).update(date_expires=None)
            AccountLink.objects.get(user=user).save()
        self.assertFalse(self.refresh().conflict)

    def test_birthday_correction(self):
        configure(self.session, eligibility=rule({"kind": "age", "op": "between", "min": 10, "max": 17}))
        recheck()
        self.assertFalse(self.refresh().conflict)
        with self.captureOnCommitCallbacks(execute=True):
            self.mia.birthday = date(2010, 1, 1)  # age 20 on the date
            self.mia.save()
        self.assertTrue(self.refresh().conflict)
        with self.captureOnCommitCallbacks(execute=True):
            self.mia.birthday = date(2016, 1, 1)
            self.mia.save()
        self.assertFalse(self.refresh().conflict)  # age 14

    def test_rule_change_on_the_session(self):
        with self.captureOnCommitCallbacks(execute=True):
            configure(self.session, eligibility=rule({"kind": "age", "op": "min", "min": 18}))
        self.assertTrue(self.refresh().conflict)
        with self.captureOnCommitCallbacks(execute=True):
            configure(self.session, eligibility={})
        self.assertFalse(self.refresh().conflict)

    def test_department_group_and_hierarchy_changes(self):
        configure(self.session, eligibility=rule({"kind": "qualification", "op": "has_any", "values": [self.gf.pk]}))
        recheck()
        self.assertTrue(self.refresh().conflict)  # Maschinist does not satisfy Gruppenführer
        with self.captureOnCommitCallbacks(execute=True):
            self.maschinist.includes.add(self.gf)  # the higher Maschinist now covers Gruppenführer
        self.assertFalse(self.refresh().conflict)
        with self.captureOnCommitCallbacks(execute=True):
            self.maschinist.includes.remove(self.gf)
        self.assertTrue(self.refresh().conflict)
        configure(self.session, eligibility=rule({"kind": "department", "op": "in", "values": [self.department.pk]}))
        recheck()
        self.assertTrue(self.refresh().conflict)
        with self.captureOnCommitCallbacks(execute=True):
            self.mia.departments.add(self.department)
        self.assertFalse(self.refresh().conflict)

    def test_hierarchy_lower_still_present(self):
        self.gf.includes.add(self.maschinist)  # Gruppenführer is higher than Maschinist
        Qualification.objects.create(type=self.gf, member=self.mia, date_acquired=date(2020, 1, 1))
        with self.captureOnCommitCallbacks(execute=True):
            Qualification.objects.filter(type=self.gf).delete()
        self.assertFalse(self.refresh().conflict)  # the lower qualification itself is still held
        with self.captureOnCommitCallbacks(execute=True):
            self.qual.delete()
        self.assertTrue(self.refresh().conflict)

    def test_higher_qualification_satisfies(self):
        self.gf.includes.add(self.maschinist)
        self.qual.delete()
        Qualification.objects.create(type=self.gf, member=self.mia, date_acquired=date(2020, 1, 1))
        recheck()
        self.assertFalse(self.refresh().conflict)

    def test_never_changes_state_and_covers_active_states_only(self):
        waiting = self.register(make_member(self.dept, "Ben"), "waitlisted")
        cancelled = self.register(make_member(self.dept, "Cleo"), "cancelled")
        before = {r.pk: (r.state, r.version) for r in Registration.objects.all()}
        result = recheck()
        self.assertEqual(set(result.conflicted), {waiting.pk})  # Mia holds the qualification
        self.assertTrue(self.refresh(waiting).conflict)
        self.assertFalse(self.refresh(cancelled).conflict)
        self.assertEqual({r.pk: (r.state, r.version) for r in Registration.objects.all()}, before)

    def test_past_unpublished_sessions_are_skipped(self):
        past = make_session(self.dept, day=timezone.localdate() - timedelta(days=2))
        draft = make_session(self.dept, day=DAY, status="draft")
        for s in (past, draft):
            configure(s, eligibility=rule({"kind": "age", "op": "min", "min": 18}))
        regs = [self.register(self.mia, session=s) for s in (past, draft)]
        recheck()
        self.assertFalse(any(self.refresh(r).conflict for r in regs))

    def test_signal_fires_once_for_newly_conflicted_only(self):
        other = self.register(make_member(self.dept, "Ben"))
        Qualification.objects.create(type=self.maschinist, member=other.member, date_acquired=date(2020, 1, 1))
        with self.captureOnCommitCallbacks(execute=True):
            configure(self.session, eligibility=rule({"kind": "age", "op": "min", "min": 18}))
        self.assertEqual(len(self.events), 1)
        session_id, ids = self.events[0]
        self.assertEqual((session_id, set(ids)), (self.session.pk, {self.reg.pk, other.pk}))
        with self.captureOnCommitCallbacks(execute=True):
            recheck()
        self.assertEqual(len(self.events), 1)  # already flagged: no second notice
        with self.captureOnCommitCallbacks(execute=True):
            configure(self.session, eligibility={})
            recheck()
        self.assertEqual(len(self.events), 1)

    def test_daily_command_is_idempotent(self):
        configure(self.session, eligibility=rule({"kind": "age", "op": "min", "min": 18}))
        out = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("recheck_registrations", stdout=out)
        self.assertIn("neu im Konflikt: 1", out.getvalue())
        self.assertTrue(self.refresh().conflict)
        out = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("recheck_registrations", stdout=out)
        self.assertIn("neu im Konflikt: 0", out.getvalue())
        self.assertIn("Konflikt aufgehoben: 0", out.getvalue())
        self.assertEqual(len(self.events), 1)

    def test_constant_query_count(self):
        def run():
            with CaptureQueriesContext(connection) as ctx:
                recheck()
            return len(ctx)

        configure(self.session, eligibility=rule({"kind": "age", "op": "min", "min": 18}))
        small = run()
        self.reg.conflict = False
        self.reg.save()
        for i in range(25):
            self.register(make_member(self.dept, f"M{i}", birthday=date(2014, 1, 1)))
        SessionParticipation.objects.update(eligibility=rule({"kind": "age", "op": "min", "min": 18}))
        Registration.objects.update(conflict=False, conflict_reasons=[])
        self.assertLessEqual(run(), small + 1)  # bulk_update is the only extra statement

    def test_portal_exposes_neutral_flag_only(self):
        from participation.portal_views import build_items

        configure(self.session, eligibility=rule({"kind": "age", "op": "min", "min": 18}))
        recheck()
        [item] = [i for i in build_items(self.mia, [self.session]) if i["id"] == self.session.pk]
        self.assertTrue(item["conflict"])
        self.assertNotIn("conflict_reasons", item)
