"""DJF annual report: counting at the reference date, movements, plausibility, snapshot. Fictional data."""

from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from departments.models import Department
from members.models import Member, Status
from membership.models import AnnualReport, MembershipEvent
from membership.services import annual_report, lifecycle
from membership.tests.test_lifecycle import role

User = get_user_model()
Kind = MembershipEvent.Kind


def by_key(rows):
    return {row["key"]: row for row in rows}


class AnnualReportTests(TestCase):
    def setUp(self):
        self.jf = Department.objects.create(name="JF Mitte", code="ar-mitte")
        self.active = Status.objects.create(name="Aktiv")

    def member(self, name, gender, birthday, joined, **extra):
        member = Member.objects.create(
            name=name, lastname="Muster", gender=gender, birthday=birthday, joined=joined, status=self.active, **extra
        )
        member.departments.add(self.jf)
        lifecycle.admit(member, on=joined)
        return member

    def test_counts_by_gender_and_age_on_the_reference_date(self):
        self.member("Mia", "female", date(2012, 12, 31), date(2020, 1, 1))  # turns 14 exactly on 31.12.2026
        self.member("Ben", "male", date(2013, 1, 1), date(2020, 1, 1))  # still 13
        self.member("Kim", "diverse", date(2007, 6, 1), date(2020, 1, 1))  # 19 → über 18
        data = annual_report.compute(self.jf, 2026)
        self.assertEqual(data["members"], {"m": 1, "w": 1, "d": 1, "total": 3})
        ages = by_key(data["age"])
        self.assertEqual((ages["14"]["w"], ages["13"]["m"], ages["gt18"]["d"]), (1, 1, 1))
        self.assertTrue(data["ok"], data["checks"])

    def test_joins_and_exits_of_the_year_balance_with_the_previous_year(self):
        stays = self.member("Mia", "female", date(2012, 3, 1), date(2020, 1, 1))
        leaves = self.member("Lea", "female", date(2011, 3, 1), date(2020, 1, 1))
        to_ea = self.member("Tom", "male", date(2008, 3, 1), date(2020, 1, 1))
        self.member("Ben", "male", date(2014, 3, 1), date(2026, 4, 1))
        lifecycle.record_exit(leaves, left_at=date(2026, 6, 30), kind=Kind.EXIT_OTHER, exit_reason="relocation")
        lifecycle.record_exit(to_ea, left_at=date(2026, 9, 1), kind=Kind.EXIT_EA)

        data = annual_report.compute(self.jf, 2026)
        movements = by_key(data["movements"])
        self.assertEqual(data["previous"]["total"], 3)
        self.assertEqual(data["previous"]["source"], "computed")
        self.assertEqual(movements["joined_new"]["m"], 1)
        self.assertEqual((movements["exit_other"]["w"], movements["exit_ea"]["m"]), (1, 1))
        self.assertEqual(by_key(data["exit_reasons"])["relocation"]["total"], 1)
        self.assertEqual(data["members"], {"m": 1, "w": 1, "d": 0, "total": 2})
        self.assertTrue(data["ok"], data["checks"])
        self.assertTrue(stays.pk)

    def test_leaving_on_the_reference_date_no_longer_counts(self):
        member = self.member("Mia", "female", date(2012, 3, 1), date(2020, 1, 1))
        lifecycle.record_exit(member, left_at=date(2026, 12, 31), kind=Kind.EXIT_OTHER, exit_reason="school")
        self.assertEqual(annual_report.compute(self.jf, 2026)["members"]["total"], 0)

    def test_transfer_from_another_department_counts_as_join(self):
        other = Department.objects.create(name="JF Nord", code="ar-nord")
        member = Member.objects.create(name="Ida", gender="female", birthday=date(2013, 1, 1), joined=date(2019, 1, 1))
        member.departments.add(other)
        lifecycle.admit(member, on=date(2019, 1, 1))
        member.departments.set([self.jf])
        lifecycle.record_department_changes(member, added={self.jf.pk}, removed={other.pk}, on=date(2026, 5, 1))
        data = annual_report.compute(self.jf, 2026)
        self.assertEqual(by_key(data["movements"])["joined_other_org"]["w"], 1)
        self.assertEqual(data["previous"]["total"], 0)
        self.assertTrue(data["ok"], data["checks"])
        nord = annual_report.compute(other, 2026)
        self.assertEqual(nord["members"]["total"], 0)
        self.assertIn("Abgang ohne Grund", {warning["message"] for warning in nord["warnings"]})

    def test_missing_gender_breaks_plausibility_and_is_listed(self):
        self.member("Ohne", "", date(2012, 3, 1), date(2020, 1, 1))
        data = annual_report.compute(self.jf, 2026)
        self.assertIn("Geschlecht fehlt", {warning["message"] for warning in data["warnings"]})

    def test_applicants_are_not_counted(self):
        applicant = Status.objects.create(name="Antrag", category=Status.Category.APPLICANT)
        self.member("Neu", "male", date(2014, 3, 1), date(2026, 3, 1)).__class__.objects.update(status=applicant)
        self.assertEqual(annual_report.compute(self.jf, 2026)["members"]["total"], 0)

    def test_anonymized_members_still_count_with_birth_year_age(self):
        self.member(
            "Ehemalig",
            "male",
            date(2012, 1, 1),
            date(2020, 1, 1),
            anonymized_at=timezone.now(),
            left_at=date(2027, 1, 1),
        )
        data = annual_report.compute(self.jf, 2026)
        self.assertEqual((data["members"]["m"], data["approximated_ages"]), (1, 1))
        self.assertEqual(by_key(data["age"])["14"]["m"], 1)

    def test_finalized_previous_year_is_used_and_cannot_be_finalized_twice(self):
        self.member("Mia", "female", date(2012, 3, 1), date(2020, 1, 1))
        with mock.patch("membership.services.annual_report.timezone.localdate", return_value=date(2026, 2, 1)):
            annual_report.finalize(self.jf, 2025)
            with self.assertRaises(ValidationError):
                annual_report.finalize(self.jf, 2025)
        AnnualReport.objects.filter(year=2025).update(
            data={**AnnualReport.objects.get(year=2025).data, "members": {"m": 0, "w": 5, "d": 0, "total": 5}}
        )
        self.assertEqual(
            annual_report.compute(self.jf, 2026)["previous"], {"m": 0, "w": 5, "d": 0, "total": 5, "source": "snapshot"}
        )

    def test_current_year_cannot_be_finalized_before_the_reference_date(self):
        with (
            mock.patch("membership.services.annual_report.timezone.localdate", return_value=date(2026, 11, 3)),
            self.assertRaises(ValidationError),
        ):
            annual_report.finalize(self.jf, 2026)


class AnnualReportApiTests(APITestCase):
    URL = "/api/v1/membership/annual-reports/"

    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="ara-mitte")
        self.nord = Department.objects.create(name="Nord", code="ara-nord")

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def test_anonymous_is_rejected(self):
        self.assertIn(
            self.client.get(f"{self.URL}preview/", {"department": self.mitte.pk, "year": 2026}).status_code, (401, 403)
        )

    def test_missing_right_is_refused(self):
        self.client.force_authenticate(self.user("ohne", self.mitte, "view_member"))
        response = self.client.get(f"{self.URL}preview/", {"department": self.mitte.pk, "year": 2026})
        self.assertEqual(response.status_code, 403)

    def test_foreign_department_is_refused(self):
        self.client.force_authenticate(self.user("nord", self.nord, "view_annualreport"))
        response = self.client.get(f"{self.URL}preview/", {"department": self.mitte.pk, "year": 2026})
        self.assertEqual(response.status_code, 403)

    def test_reader_sees_preview_and_exports_excel(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_annualreport"))
        response = self.client.get(f"{self.URL}preview/", {"department": self.mitte.pk, "year": 2026})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["year"], 2026)
        export = self.client.get(f"{self.URL}export/", {"department": self.mitte.pk, "year": 2026})
        self.assertEqual(export.status_code, 200)
        self.assertTrue(export.content.startswith(b"PK"))

    def test_manual_values_need_the_change_right(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_annualreport"))
        body = {"department": self.mitte.pk, "year": 2026, "supervisors": {"m": 2, "w": 1}}
        self.assertEqual(self.client.post(f"{self.URL}manual/", body, format="json").status_code, 403)
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_annualreport", "change_annualreport"))
        response = self.client.post(f"{self.URL}manual/", body, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["manual"]["supervisors"], {"m": 2, "w": 1, "d": 0, "total": 3})

    def test_finalize_needs_its_own_right(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_annualreport", "change_annualreport"))
        body = {"department": self.mitte.pk, "year": 2025}
        self.assertEqual(self.client.post(f"{self.URL}finalize/", body, format="json").status_code, 403)
        self.client.force_authenticate(self.user("jugendwart", self.mitte, "finalize_annualreport"))
        response = self.client.post(f"{self.URL}finalize/", body, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["state"], "final")


class ImplicitMovementTests(TestCase):
    def test_dates_without_movements_still_balance(self):
        jf = Department.objects.create(name="JF", code="ar-implicit")
        status = Status.objects.create(name="Aktiv")
        joined = Member.objects.create(
            name="Alt", gender="male", birthday=date(2013, 1, 1), joined=date(2026, 3, 1), status=status
        )
        left = Member.objects.create(
            name="Weg",
            gender="female",
            birthday=date(2012, 1, 1),
            joined=date(2020, 1, 1),
            left_at=date(2026, 5, 1),
            status=status,
        )
        for member in (joined, left):
            member.departments.add(jf)
        data = annual_report.compute(jf, 2026)
        movements = by_key(data["movements"])
        self.assertEqual((movements["joined_new"]["m"], movements["exit_other"]["w"]), (1, 1))
        self.assertTrue(data["checks"][1]["ok"] and data["checks"][3]["ok"], data["checks"])
        messages = {warning["message"] for warning in data["warnings"]}
        self.assertIn("Austritt ohne Abgangsart und Grund", messages)
