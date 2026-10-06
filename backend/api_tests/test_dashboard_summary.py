"""
UX-01.1: dashboard summary counts follow the list endpoints' rights and department scope.

Fictional data only.
"""

from datetime import date, timedelta

from django.utils import timezone

from members.models import MemberList, MemberListEntry
from orders.models import Order, OrderableItem, OrderItem, OrderStatus
from qualifications.models import Qualification
from servicebook.models import Service

from .test_qualifications_department_scope import QualificationDeptScopeBase

URL = "/api/v1/dashboard/summary/"


class DashboardSummaryTests(QualificationDeptScopeBase):
    def setUp(self):
        super().setUp()
        today = date.today()
        # Member A: expires in 10 days; member B: expired but renewed -> nothing expired.
        Qualification.objects.create(
            type=self.qual_type,
            member=self.member_a,
            date_acquired=today - timedelta(days=700),
            date_expires=today + timedelta(days=10),
        )
        Qualification.objects.create(
            type=self.qual_type,
            member=self.member_b,
            date_acquired=today - timedelta(days=900),
            date_expires=today - timedelta(days=5),
        )
        Qualification.objects.create(
            type=self.qual_type,
            member=self.member_b,
            date_acquired=today,
            date_expires=today + timedelta(days=700),
        )

        now = timezone.now()
        for days in (3, 20, -2):
            Service.objects.create(
                start=now + timedelta(days=days),
                end=now + timedelta(days=days, hours=2),
                topic=f"Dienst {days}",
                department=self.dept_a,
            )

        open_list = MemberList.objects.create(name="Offen", department=self.dept_a)
        MemberListEntry.objects.create(member_list=open_list, member=self.member_a, checked=False)
        done_list = MemberList.objects.create(name="Erledigt", department=self.dept_a)
        MemberListEntry.objects.create(member_list=done_list, member=self.member_a, checked=True)

        status_new = OrderStatus.objects.get_or_create(code="NEW", defaults={"name": "Neu"})[0]
        item = OrderableItem.objects.create(name="Helm", category="Schutz")
        open_order = Order.objects.create(member=self.member_a, department=self.dept_a)
        OrderItem.objects.create(order=open_order, item=item, status=status_new)
        delivered = Order.objects.create(member=self.member_a, department=self.dept_a)
        OrderItem.objects.create(order=delivered, item=item, status=status_new, delivered_date=now)

    def test_counts_for_organisation_wide_user(self):
        self.client.force_authenticate(self.org_wide_user)
        data = self.client.get(URL).data
        self.assertEqual(data["members"], {"total": 2})
        self.assertEqual(data["qualifications"]["expired"], 0, "renewed qualification is not expired")
        self.assertEqual(data["qualifications"]["expiring"], {"30": 1, "60": 1, "90": 1})
        self.assertEqual(data["services"]["upcoming"], 1)
        self.assertEqual(data["services"]["next"]["topic"], "Dienst 3")
        self.assertEqual(data["orders"], {"open": 1})
        self.assertEqual(data["lists"], {"open": 1})

    def test_sections_without_right_are_null_and_scope_is_kept(self):
        # Department A user who may only view qualifications.
        self.client.force_authenticate(self.dept_a_admin)
        data = self.client.get(URL).data
        for section in ("members", "parents", "services", "orders", "lists"):
            self.assertIsNone(data[section], section)
        self.assertEqual(data["qualifications"]["expiring"]["30"], 1)
        self.assertEqual(data["qualifications"]["without_evidence"], 1, "only the current department A record")

    def test_contains_counts_only(self):
        self.client.force_authenticate(self.org_wide_user)
        body = self.client.get(URL).content.decode()
        self.assertNotIn("Anna", body)
        self.assertNotIn("Dept-A", body)

    def test_requires_login(self):
        self.assertIn(self.client.get(URL).status_code, (401, 403))
