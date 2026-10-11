"""PART-04: free places, staffing at risk and published assignments reach the right people."""

from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.utils import timezone

from departments.models import Department, UserDepartmentRole
from members.models import Member
from notifications.models import EmailDelivery, InboxItem
from participation import service
from participation.models import Slot
from participation.tests.helpers import configure, future_day, make_session
from portal.models import AccountLink

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SlotProducerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="Mitte")
        planners = Group.objects.create(name="Planung")
        planners.permissions.add(Permission.objects.get(codename="can_manage_training"))
        cls.leader = User.objects.create_user("leitung", email="leitung@example.invalid", password="x")
        UserDepartmentRole.objects.create(user=cls.leader, department=cls.dept).groups.add(planners)
        cls.ada = Member.objects.create(name="Ada", lastname="Test")
        cls.ben = Member.objects.create(name="Ben", lastname="Test")
        for member in (cls.ada, cls.ben):
            member.departments.add(cls.dept)
        cls.ben_user = User.objects.create_user(
            "ben@example.invalid", email="ben@example.invalid", password="x", account_kind="portal"
        )
        AccountLink.objects.create(user=cls.ben_user, member=cls.ben, status="confirmed")

    def session(self, **kw):
        with self.captureOnCommitCallbacks(execute=True):
            session = make_session(self.dept, created_by=self.leader, title="Wache", **kw)
        return session

    def test_manual_waiting_list_creates_a_staffing_task(self):
        session = self.session(day=future_day(10))
        participation = configure(session, mode="opt_in", waitlist_mode="manual", max_participants=1)
        crew = Slot.objects.create(participation=participation, label="Trupp", max_count=1)
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(session.pk, self.ada.pk, "registered", actor=None, source="staff", slot=crew.pk)
            service.set_registration(session.pk, self.ben.pk, "registered", actor=None, source="staff", slot=crew.pk)
        placed = EmailDelivery.objects.get(kind="waitlist_placed", user=self.ben_user)
        self.assertEqual(placed.context["waitlist"]["slot"], "Trupp")
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(session.pk, self.ada.pk, "cancelled", actor=None, source="staff")
        task = InboxItem.objects.get(kind="slot_free_manual")
        self.assertEqual(task.item_type, "task")
        self.assertIn("Trupp", task.title)
        self.assertTrue(EmailDelivery.objects.filter(kind="slot_free_manual", user=self.leader).exists())
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(session.pk, self.ben.pk, "registered", actor=self.leader, source="staff")
        self.assertTrue(EmailDelivery.objects.filter(kind="waitlist_promoted", user=self.ben_user).exists())

    def test_short_notice_cancellation_reports_missing_positions(self):
        start = (timezone.localtime() + timedelta(hours=20)).replace(second=0, microsecond=0)
        end = time(23, 59) if start.hour == 23 else start.replace(hour=start.hour + 1).time()
        session = self.session(day=start.date(), start=start.time(), end=end)
        participation = configure(session, mode="opt_in", max_participants=1)
        lead = Slot.objects.create(participation=participation, label="Wachführung", min_count=1, max_count=1)
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(session.pk, self.ada.pk, "registered", actor=None, source="staff", slot=lead.pk)
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(session.pk, self.ada.pk, "cancelled", actor=None, source="portal_member")
        self.assertTrue(InboxItem.objects.filter(kind="staffing_at_risk", item_type="task").exists())
        mail = EmailDelivery.objects.get(kind="reg_cancelled", user=self.leader)
        self.assertEqual(mail.context["staffing"]["missing"], [{"label": "Wachführung", "count": 1}])
