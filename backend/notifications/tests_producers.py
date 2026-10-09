"""NOTIF-01.5b: participation events reach parents, members and responsible staff."""

from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent
from notifications.dispatch import deliver_emails
from notifications.models import EmailDelivery, InboxItem, InboxRecipient
from participation import service
from participation.tests.helpers import configure, future_day, make_session
from portal.models import AccountLink

User = get_user_model()


def born(years):
    today = timezone.localdate()
    return date(today.year - years, today.month, min(today.day, 28))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ProducerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        planners = Group.objects.create(name="Planung")
        planners.permissions.add(Permission.objects.get(codename="can_manage_training"))
        cls.leader = User.objects.create_user(
            "leitung", email="leitung@example.invalid", password="x", first_name="Lea"
        )
        UserDepartmentRole.objects.create(user=cls.leader, department=cls.mitte).groups.add(planners)
        cls.deputy = User.objects.create_user("vertretung", email="vertretung@example.invalid", password="x")
        UserDepartmentRole.objects.create(user=cls.deputy, department=cls.mitte).groups.add(planners)
        cls.child = Member.objects.create(name="Mia", lastname="Becker", birthday=born(12))
        cls.child.departments.add(cls.mitte)
        cls.adult = Member.objects.create(name="Tom", lastname="Becker", birthday=born(19))
        cls.adult.departments.add(cls.mitte)
        parent = Parent.objects.create(name="Sandra", lastname="Becker", email="sandra@example.invalid")
        parent.children.add(cls.child, cls.adult)
        cls.parent_user = User.objects.create_user(
            "sandra@example.invalid",
            email="sandra@example.invalid",
            password="x",
            account_kind="portal",
            first_name="Sandra",
        )
        AccountLink.objects.create(user=cls.parent_user, parent=parent, status="confirmed")

    def publish(self, **kw):
        with self.captureOnCommitCallbacks(execute=True):
            session = make_session(
                self.mitte, day=kw.pop("day", future_day(10)), created_by=self.leader, title="Knoten", **kw
            )
        return session

    def test_new_service_reaches_the_parent_of_visible_children_only(self):
        self.publish()
        notices = InboxItem.objects.filter(kind="session_published")
        self.assertEqual(notices.count(), 1)  # Tom is an adult: no parent notice for him
        self.assertIn("Mia", notices.get().title)
        self.assertTrue(InboxRecipient.objects.filter(item=notices.get(), user=self.parent_user).exists())
        self.assertEqual(deliver_emails(), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["sandra@example.invalid"])
        self.assertIn("Mia abmelden", message.body)  # opt-out default: always a cancellation link (E17)
        self.assertIn("Benachrichtigungen einstellen", message.body)

    def test_ineligible_people_are_not_invited(self):
        with self.captureOnCommitCallbacks(execute=True):
            session = make_session(self.mitte, day=future_day(10), status="draft", created_by=self.leader)
            configure(
                session,
                mode="opt_in",
                eligibility={"v": 1, "match": "all", "rules": [{"kind": "age", "op": "min", "min": 16}]},
            )
        with self.captureOnCommitCallbacks(execute=True):
            session.status = "published"
            session.save()
        self.assertFalse(InboxItem.objects.filter(kind="session_published").exists())

    def test_waitlist_and_promotion_notify_the_family(self):
        session = self.publish()
        configure(session, mode="opt_in", max_participants=1)
        other = Member.objects.create(name="Ben", lastname="X", birthday=born(13))
        other.departments.add(self.mitte)
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(session.pk, other.pk, "registered", actor=self.leader, source="staff")
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(
                session.pk, self.child.pk, "registered", actor=self.parent_user, source="portal_parent"
            )
        self.assertTrue(InboxItem.objects.filter(kind="waitlist_placed").exists())
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(session.pk, other.pk, "cancelled", actor=self.leader, source="staff")
        self.assertTrue(InboxItem.objects.filter(kind="waitlist_promoted", title__contains="Mia").exists())
        kinds = set(EmailDelivery.objects.filter(user=self.parent_user).values_list("kind", flat=True))
        self.assertLessEqual({"waitlist_placed", "waitlist_promoted"}, kinds)

    def test_short_notice_cancellation_alerts_responsibles(self):
        # Inside the 24 h window whatever the time of day (a fixed "tomorrow 18:00" only failed before 18:00).
        start = (timezone.localtime() + timedelta(hours=20)).replace(second=0, microsecond=0)
        end = time(23, 59) if start.hour == 23 else start.replace(hour=start.hour + 1).time()
        session = self.publish(day=start.date(), start=start.time(), end=end)
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(
                session.pk,
                self.child.pk,
                "cancelled",
                actor=self.parent_user,
                source="portal_parent",
                reason_category="krankheit",
            )
        item = InboxItem.objects.get(kind="reg_cancelled")
        self.assertEqual(item.group_key, f"reg_cancelled:session:{session.pk}")
        self.assertEqual(set(item.recipients.values_list("user__username", flat=True)), {"leitung", "vertretung"})
        self.assertEqual(
            list(EmailDelivery.objects.filter(kind="reg_cancelled").values_list("user__username", flat=True)),
            ["leitung"],
        )
        deliver_emails()
        self.assertIn("Krankheit", mail.outbox[-1].body)
        self.assertNotIn("sandra", mail.outbox[-1].to[0])

    def test_early_cancellation_only_reaches_the_inbox(self):
        session = self.publish(day=future_day(20))
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(
                session.pk, self.child.pk, "cancelled", actor=self.parent_user, source="portal_parent"
            )
        self.assertTrue(InboxItem.objects.filter(kind="reg_cancelled").exists())
        self.assertFalse(EmailDelivery.objects.filter(kind="reg_cancelled").exists())

    def test_cancelled_service_is_announced(self):
        session = self.publish()
        with self.captureOnCommitCallbacks(execute=True):
            session.status = "cancelled"
            session.save()
        item = InboxItem.objects.get(kind="session_changed")
        self.assertTrue(item.title.startswith("Abgesagt"))
        deliver_emails()
        self.assertTrue(any("fällt aus" in m.body for m in mail.outbox))

    def test_mail_links_resolve_for_the_addressed_account(self):
        import re

        from rest_framework.test import APIClient

        self.publish()
        deliver_emails()
        tokens = re.findall(r"/a/([\w:.-]+)", mail.outbox[0].body)
        self.assertTrue(tokens)
        client = APIClient()
        client.force_authenticate(self.parent_user)
        actions = {
            t: client.post("/api/v1/actions/resolve/", {"token": t}, format="json").json().get("action") for t in tokens
        }
        cancel = [t for t, action in actions.items() if action == "cancel"]
        self.assertTrue(cancel, f"Abmeldelink fehlt oder ist nicht auflösbar: {actions}")
        other = APIClient()
        other.force_authenticate(self.leader)
        self.assertEqual(other.post("/api/v1/actions/resolve/", {"token": cancel[0]}, format="json").status_code, 403)
