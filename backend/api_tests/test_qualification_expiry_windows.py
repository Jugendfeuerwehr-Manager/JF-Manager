"""
UX-06.1: expiry windows, renewals and missing evidence for qualifications.

Fictional data only.
"""

from datetime import date, timedelta

from django.contrib.contenttypes.models import ContentType

from members.models import Attachment
from qualifications.models import Qualification

from .test_qualifications_department_scope import QualificationDeptScopeBase


class QualificationExpiryWindowTests(QualificationDeptScopeBase):
    def setUp(self):
        super().setUp()
        Qualification.objects.all().delete()
        today = date.today()

        def qual(member, acquired_days_ago, expires_in):
            return Qualification.objects.create(
                type=self.qual_type,
                member=member,
                date_acquired=today - timedelta(days=acquired_days_ago),
                date_expires=today + timedelta(days=expires_in),
            )

        self.in_20 = qual(self.member_a, 700, 20)
        self.in_50 = Qualification.objects.create(
            type=self.qual_type.__class__.objects.create(name="Sprechfunk", expires=False),
            member=self.member_a,
            date_acquired=today - timedelta(days=300),
            date_expires=today + timedelta(days=50),
        )
        # Expired, then renewed: only the renewal is current.
        self.renewed_old = qual(self.member_b, 800, -10)
        self.renewed_new = qual(self.member_b, 5, 85)
        Attachment.objects.create(
            content_type=ContentType.objects.get_for_model(Qualification), object_id=self.in_20.id, name="Nachweis.pdf"
        )

    def ids(self, query, user=None):
        self.client.force_authenticate(user or self.org_wide_user)
        response = self.client.get(f"/api/v1/qualifications/?{query}")
        self.assertEqual(response.status_code, 200, response.data)
        return {row["id"] for row in response.data["results"]}

    def test_expiry_windows_include_shorter_windows(self):
        self.assertEqual(self.ids("expiring_within=30"), {self.in_20.id})
        self.assertEqual(self.ids("expiring_within=60"), {self.in_20.id, self.in_50.id})
        self.assertEqual(self.ids("expiring_within=90"), {self.in_20.id, self.in_50.id, self.renewed_new.id})

    def test_rejects_other_windows(self):
        self.client.force_authenticate(self.org_wide_user)
        self.assertEqual(self.client.get("/api/v1/qualifications/?expiring_within=7").status_code, 400)

    def test_current_hides_renewed_records_but_history_stays_listed(self):
        self.assertNotIn(self.renewed_old.id, self.ids("current=true"))
        self.assertIn(self.renewed_old.id, self.ids(f"member={self.member_b.id}"))

    def test_without_evidence_and_list_flag(self):
        self.assertNotIn(self.in_20.id, self.ids("without_evidence=true"))
        self.client.force_authenticate(self.org_wide_user)
        rows = {row["id"]: row for row in self.client.get("/api/v1/qualifications/").data["results"]}
        self.assertTrue(rows[self.in_20.id]["has_evidence"])
        self.assertFalse(rows[self.in_50.id]["has_evidence"])
        self.assertEqual(rows[self.in_50.id]["member"], self.member_a.id)

    def test_statistics_count_current_records_per_window(self):
        self.client.force_authenticate(self.org_wide_user)
        data = self.client.get("/api/v1/qualifications/statistics/").data
        self.assertEqual(data["expired_qualifications"], 0, "renewed qualification must not count as expired")
        self.assertEqual(data["expiring_by_window"], {"30": 1, "60": 2, "90": 3})
        self.assertEqual(data["without_evidence"], 2)

    def test_statistics_stay_in_department_scope(self):
        self.client.force_authenticate(self.dept_a_admin)
        data = self.client.get("/api/v1/qualifications/statistics/").data
        self.assertEqual(data["expiring_by_window"], {"30": 1, "60": 2, "90": 2})
        self.assertEqual(self.ids("expiring_within=90", self.dept_a_admin), {self.in_20.id, self.in_50.id})
