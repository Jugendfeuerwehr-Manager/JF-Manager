from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from members.models import Member
from participation.eligibility import (
    NEUTRAL_AUDIENCE_NOTICE,
    age_on,
    evaluate,
    evaluate_members,
    load_facts,
    neutral_audience_notice,
)
from portal.models import AccountLink
from qualifications.models import Qualification, SpecialTask

from .test_rules import RuleFixtureMixin, rule

DAY = date(2026, 10, 10)


class EvaluationTests(RuleFixtureMixin, TestCase):
    def member(self, **kwargs):
        return Member.objects.create(name="Max", lastname="Muster", **kwargs)

    def check(self, r, member, day=DAY):
        return evaluate_members(r, [member.pk], day)[member.pk]

    def has(self, *types, op="has_any", kind="qualification"):
        return rule({"kind": kind, "op": op, "values": [t.pk for t in types]})

    def test_qualification_expiry_boundaries(self):
        m = self.member()
        q = Qualification.objects.create(
            type=self.maschinist, member=m, date_acquired=date(2020, 1, 1), date_expires=DAY
        )
        self.assertTrue(self.check(self.has(self.maschinist), m).ok)  # expires exactly on the day
        q.date_expires = date(2026, 10, 9)
        q.save()
        res = self.check(self.has(self.maschinist), m)
        self.assertFalse(res.ok)
        self.assertEqual(res.reasons, ["Qualifikation ‚Maschinist‘: Gültig nur bis 09.10.2026"])

    def test_qualification_not_yet_acquired_and_missing(self):
        m = self.member()
        self.assertEqual(self.check(self.has(self.maschinist), m).reasons, ["Qualifikation ‚Maschinist‘ fehlt"])
        Qualification.objects.create(type=self.maschinist, member=m, date_acquired=date(2026, 10, 11))
        self.assertEqual(
            self.check(self.has(self.maschinist), m).reasons, ["Qualifikation ‚Maschinist‘: Gültig erst ab 11.10.2026"]
        )
        self.assertTrue(self.check(self.has(self.maschinist), m, date(2026, 10, 11)).ok)

    def test_has_all_and_has_none(self):
        m = self.member()
        Qualification.objects.create(type=self.gf, member=m, date_acquired=date(2020, 1, 1))
        res = self.check(self.has(self.gf, self.zf, op="has_all"), m)
        self.assertEqual(res.reasons, ["Qualifikation ‚Zugführer‘ fehlt"])
        res = self.check(self.has(self.gf, op="has_none"), m)
        self.assertFalse(res.ok)
        self.assertTrue(self.check(self.has(self.zf, op="has_none"), m).ok)
        res = self.check(self.has(self.gf, self.zf), m)
        self.assertTrue(res.ok)
        res = self.check(self.has(self.zf, self.maschinist), m)
        self.assertEqual(res.reasons, ["Keine der Qualifikationen ‚Zugführer‘ oder ‚Maschinist‘ vorhanden"])

    def test_special_task(self):
        m = self.member()
        SpecialTask.objects.create(task=self.task, member=m, start_date=date(2026, 1, 1), end_date=date(2026, 10, 9))
        r = self.has(self.task, kind="special_task")
        self.assertEqual(self.check(r, m).reasons, ["Sonderaufgabe ‚Jugendsprecher‘: Gültig nur bis 09.10.2026"])
        self.assertTrue(self.check(r, m, date(2026, 10, 9)).ok)

    def test_account_qualification_only_via_confirmed_link(self):
        User = get_user_model()
        m = self.member()
        user = User.objects.create_user("betreuer")
        Qualification.objects.create(type=self.maschinist, user=user, date_acquired=date(2020, 1, 1))
        SpecialTask.objects.create(task=self.task, user=user, start_date=date(2020, 1, 1))
        link = AccountLink.objects.create(user=user, member=m, status=AccountLink.Status.PENDING)
        self.assertFalse(self.check(self.has(self.maschinist), m).ok)
        for status in (AccountLink.Status.REJECTED, AccountLink.Status.PENDING):
            link.status = status
            link.save()
            self.assertFalse(self.check(self.has(self.maschinist), m).ok)
        link.status = AccountLink.Status.CONFIRMED
        link.save()
        self.assertTrue(self.check(self.has(self.maschinist), m).ok)
        self.assertTrue(self.check(self.has(self.task, kind="special_task"), m).ok)

    def test_account_and_member_entries_merge_and_do_not_leak(self):
        User = get_user_model()
        m, other = self.member(), self.member()
        user = User.objects.create_user("betreuer")
        AccountLink.objects.create(user=user, member=m, status=AccountLink.Status.CONFIRMED)
        Qualification.objects.create(type=self.gf, user=user, date_acquired=date(2020, 1, 1))
        Qualification.objects.create(type=self.zf, member=m, date_acquired=date(2020, 1, 1))
        self.assertTrue(self.check(self.has(self.gf, self.zf, op="has_all"), m).ok)
        self.assertFalse(self.check(self.has(self.gf), other).ok)

    def test_missing_birthday_and_gender(self):
        m = self.member()
        age = rule({"kind": "age", "op": "min", "min": 10})
        self.assertEqual(self.check(age, m).reasons, ["Geburtsdatum ist nicht erfasst"])
        gender = rule({"kind": "gender", "op": "in", "values": ["male"]})
        self.assertEqual(self.check(gender, m).reasons, ["Geschlecht ist nicht erfasst"])

    def test_gender(self):
        f = self.member(gender="female")
        r = rule({"kind": "gender", "op": "in", "values": ["female", "diverse"]})
        self.assertTrue(self.check(r, f).ok)
        res = self.check(rule({"kind": "gender", "op": "in", "values": ["male"]}), f)
        self.assertEqual(res.reasons, ["Nur für Teilnehmende des Geschlechts männlich"])

    def test_age_boundaries(self):
        r = rule({"kind": "age", "op": "between", "min": 10, "max": 17})
        # 10th birthday exactly on the session day
        self.assertTrue(self.check(r, self.member(birthday=date(2016, 10, 10))).ok)
        res = self.check(r, self.member(birthday=date(2016, 10, 11)))  # turns 10 the day after
        self.assertEqual(res.reasons, ["Nur für Teilnehmende von 10 bis 17 Jahren"])
        self.assertTrue(self.check(r, self.member(birthday=date(2008, 10, 11))).ok)  # still 17
        self.assertFalse(self.check(r, self.member(birthday=date(2008, 10, 10))).ok)  # turned 18 today
        self.assertEqual(
            self.check(rule({"kind": "age", "op": "min", "min": 18}), self.member(birthday=date(2010, 1, 1))).reasons,
            ["Nur für Teilnehmende ab 18 Jahren"],
        )
        self.assertEqual(
            self.check(rule({"kind": "age", "op": "max", "max": 12}), self.member(birthday=date(2000, 1, 1))).reasons,
            ["Nur für Teilnehmende bis 12 Jahre"],
        )

    def test_leap_day_birthday(self):
        born = date(2008, 2, 29)
        self.assertEqual(age_on(born, date(2026, 2, 28)), 17)
        self.assertEqual(age_on(born, date(2026, 3, 1)), 18)
        self.assertEqual(age_on(born, date(2028, 2, 29)), 20)
        self.assertEqual(age_on(born, date(2028, 2, 28)), 19)
        r = rule({"kind": "age", "op": "min", "min": 18})
        m = self.member(birthday=born)
        self.assertFalse(self.check(r, m, date(2026, 2, 28)).ok)
        self.assertTrue(self.check(r, m, date(2026, 3, 1)).ok)

    def test_group_status_department(self):
        from departments.models import Department

        m = self.member(group=self.group, status=self.status)
        m.departments.add(self.department)
        r = rule(
            {"kind": "group", "op": "in", "values": [self.group.pk]},
            {"kind": "status", "op": "in", "values": [self.status.pk]},
            {"kind": "department", "op": "in", "values": [self.department.pk]},
        )
        self.assertTrue(self.check(r, m).ok)
        bare = self.member()
        self.assertEqual(
            self.check(r, bare).reasons,
            ["Gruppe ist nicht erfasst", "Status ist nicht erfasst", "Keiner Abteilung zugeordnet"],
        )
        other = Department.objects.create(name="Andere", code="andere")
        r = rule({"kind": "department", "op": "in", "values": [other.pk]})
        self.assertEqual(self.check(r, m).reasons, ["Nur für die Abteilung ‚Andere‘"])

    def test_two_levels_any_all(self):
        m = self.member(birthday=date(2000, 1, 1))
        Qualification.objects.create(type=self.maschinist, member=m, date_acquired=date(2020, 1, 1))
        Qualification.objects.create(type=self.zf, member=m, date_acquired=date(2020, 1, 1))
        group = {
            "match": "any",
            "rules": [
                {"kind": "qualification", "op": "has_any", "values": [self.gf.pk]},
                {"kind": "qualification", "op": "has_any", "values": [self.zf.pk]},
            ],
        }
        r = rule(
            {"kind": "qualification", "op": "has_any", "values": [self.maschinist.pk]},
            group,
            {"kind": "age", "op": "min", "min": 18},
        )
        self.assertTrue(self.check(r, m).ok)
        # Without the Zugführer both alternatives fail: one reason naming both.
        Qualification.objects.filter(type=self.zf).delete()
        res = self.check(r, m)
        self.assertFalse(res.ok)
        self.assertEqual(len(res.reasons), 1)
        self.assertTrue(res.reasons[0].startswith("Keine der Alternativen erfüllt: "))
        self.assertIn("Gruppenführer", res.reasons[0])
        self.assertIn("Zugführer", res.reasons[0])
        # Top-level any: the age alone is enough.
        self.assertTrue(self.check({**r, "match": "any"}, m).ok)
        young = self.member(birthday=date(2015, 1, 1))
        self.assertFalse(self.check({**r, "match": "any"}, young).ok)

    def test_empty_rule_is_eligible(self):
        self.assertTrue(self.check(rule(), self.member()).ok)

    def test_load_facts_query_count_is_constant(self):
        User = get_user_model()
        for n in (3, 40):
            Member.objects.all().delete()
            members = [self.member(birthday=date(2010, 1, 1), group=self.group) for _ in range(n)]
            for i, m in enumerate(members):
                m.departments.add(self.department)
                Qualification.objects.create(type=self.gf, member=m, date_acquired=date(2020, 1, 1))
                user = User.objects.create_user(f"u{n}-{i}")
                AccountLink.objects.create(user=user, member=m, status="confirmed")
                SpecialTask.objects.create(task=self.task, user=user, start_date=date(2020, 1, 1))
            with self.assertNumQueries(5):
                facts = load_facts([m.pk for m in members])
            self.assertEqual(len(facts), n)

    def test_neutral_wording(self):
        self.assertIsNone(neutral_audience_notice(rule({"kind": "age", "op": "min", "min": 1})))
        r = rule({"match": "any", "rules": [{"kind": "gender", "op": "in", "values": ["male"]}]})
        self.assertEqual(neutral_audience_notice(r), NEUTRAL_AUDIENCE_NOTICE)
        self.assertEqual(NEUTRAL_AUDIENCE_NOTICE, "Dieser Dienst richtet sich an eine bestimmte Teilnehmendengruppe")

    def test_evaluate_is_pure_with_names(self):
        from participation.rules import Names

        facts = load_facts([self.member().pk])
        (person,) = facts.values()
        r = self.has(self.maschinist)
        names = Names.for_rule(r)
        with self.assertNumQueries(0):
            self.assertFalse(evaluate(r, person, DAY, names).ok)


class HierarchyEvaluationTests(RuleFixtureMixin, TestCase):
    """E18: higher qualifications satisfy requirements on lower ones."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from qualifications.models import QualificationType

        cls.trupp = QualificationType.objects.create(name="Truppmann")
        cls.tf = QualificationType.objects.create(name="Truppführer")
        cls.gruf = QualificationType.objects.create(name="Gruppenführer ")
        cls.zuf = QualificationType.objects.create(name="Zugführer ")
        cls.tf.includes.add(cls.trupp)
        cls.gruf.includes.add(cls.tf)
        cls.zuf.includes.add(cls.gruf)

    def person(self, qual_type=None, start=date(2020, 1, 1), end=None):
        m = Member.objects.create(name="Max", lastname="Muster")
        if qual_type:
            Qualification.objects.create(type=qual_type, member=m, date_acquired=start, date_expires=end)
        return m

    def check(self, r, member, day=DAY):
        return evaluate_members(r, [member.pk], day)[member.pk]

    def has(self, *types, op="has_any"):
        return rule({"kind": "qualification", "op": op, "values": [t.pk for t in types]})

    def test_three_level_chain(self):
        for held in (self.trupp, self.tf, self.gruf, self.zuf):
            self.assertTrue(self.check(self.has(self.trupp), self.person(held)).ok, held)
        self.assertFalse(self.check(self.has(self.zuf), self.person(self.trupp)).ok)
        self.assertFalse(self.check(self.has(self.tf), self.person(self.trupp)).ok)
        self.assertTrue(self.check(self.has(self.tf), self.person(self.zuf)).ok)

    def test_reason_names_substitute(self):
        res = self.check(self.has(self.trupp, op="has_all"), self.person(self.tf))
        self.assertTrue(res.ok)
        self.assertEqual(res.notes, ["Qualifikation ‚Truppmann‘ erfüllt durch ‚Truppführer‘"])

    def test_direct_holder_has_no_note(self):
        self.assertEqual(self.check(self.has(self.trupp), self.person(self.trupp)).notes, [])

    def test_missing_keeps_existing_reason(self):
        res = self.check(self.has(self.trupp), self.person())
        self.assertEqual(res.reasons, ["Qualifikation ‚Truppmann‘ fehlt"])

    def test_higher_expired_and_lower_missing_fails(self):
        m = self.person(self.zuf, end=date(2026, 1, 31))
        res = self.check(self.has(self.trupp), m)
        self.assertFalse(res.ok)
        self.assertEqual(res.reasons, ["Qualifikation ‚Truppmann‘: Gültig nur bis 31.01.2026"])

    def test_lower_valid_when_higher_expired(self):
        m = self.person(self.zuf, end=date(2026, 1, 31))
        Qualification.objects.create(type=self.trupp, member=m, date_acquired=date(2020, 1, 1))
        self.assertTrue(self.check(self.has(self.trupp), m).ok)

    def test_has_none_excludes_higher(self):
        r = self.has(self.trupp, op="has_none")
        res = self.check(r, self.person(self.gruf))
        self.assertFalse(res.ok)
        self.assertEqual(
            res.reasons,
            ["Qualifikation ‚Gruppenführer ‘ schließt ‚Truppmann‘ ein und schließt die Teilnahme aus"],
        )
        self.assertTrue(self.check(r, self.person()).ok)
        self.assertTrue(self.check(self.has(self.zuf, op="has_none"), self.person(self.trupp)).ok)

    def test_summary_or_higher(self):
        from participation.rules import summarize

        self.assertEqual(summarize(self.has(self.trupp)), "Truppmann (oder höher)")
        self.assertEqual(summarize(self.has(self.zuf)), "Zugführer ")
        self.assertEqual(summarize(self.has(self.trupp, op="has_none")), "ohne Qualifikation Truppmann")

    def test_query_count_constant(self):
        def count(n):
            Member.objects.all().delete()
            ids = [self.person(self.tf).pk for _ in range(n)]
            with CaptureQueriesContext(connection) as ctx:
                evaluate_members(self.has(self.trupp), ids, DAY)
            return len(ctx)

        self.assertEqual(count(3), count(40))
