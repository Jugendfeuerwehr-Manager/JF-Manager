"""NOTIF-02: registrations, applications and cancellations reach all staff, admins included."""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, RoleTemplate, UserDepartmentRole
from members.models import Group
from notifications.dispatch import deliver_emails
from notifications.models import EmailDelivery, InboxItem, InboxRecipient
from participation import assignment, service
from participation.tests.helpers import configure, future_day, make_member, make_session

User = get_user_model()


def later():
    return timezone.now() + timedelta(minutes=10)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class StaffRegistrationNoticeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.dept = Department.objects.create(name="Mitte", code="m")
        cls.other = Department.objects.create(name="Nord", code="n")
        planner_group = RoleTemplate.objects.get(key="training_planner").group
        cls.lead = User.objects.create_user("leitung", email="leitung@example.invalid", first_name="Lea")
        UserDepartmentRole.objects.create(user=cls.lead, department=cls.dept).groups.add(planner_group)
        cls.deputy = User.objects.create_user("vertretung", email="vertretung@example.invalid")
        UserDepartmentRole.objects.create(user=cls.deputy, department=cls.dept).groups.add(planner_group)
        cls.foreign = User.objects.create_user("nord", email="nord@example.invalid")
        UserDepartmentRole.objects.create(user=cls.foreign, department=cls.other).groups.add(planner_group)
        cls.admin = User.objects.create_superuser("admin", "admin@example.invalid", "x")
        cls.group = Group.objects.create(name="Rot", department=cls.dept)
        cls.mia = make_member(cls.dept, "Mia", cls.group)
        cls.ole = make_member(cls.dept, "Ole", cls.group)

    def session(self, **values):
        session = make_session(self.dept, day=future_day(20), groups=[self.group], created_by=self.lead, title="Wache")
        configure(session, **values)
        return session

    def change(self, session, member, target, actor=None, source="portal_member", **kw):
        with self.captureOnCommitCallbacks(execute=True):
            return service.set_registration(session.pk, member.pk, target, actor=actor, source=source, **kw)

    def mailed(self, kind):
        return set(EmailDelivery.objects.filter(kind=kind).values_list("user__username", flat=True))

    def test_registration_reaches_all_staff_including_admin(self):
        session = self.session(mode="opt_in")
        self.change(session, self.mia, "registered")
        item = InboxItem.objects.get(kind="reg_received")
        self.assertEqual((item.item_type, item.category), ("notice", "registrations"))
        recipients = set(InboxRecipient.objects.filter(item=item).values_list("user__username", flat=True))
        self.assertEqual(recipients, {"leitung", "vertretung", "admin"})
        self.assertEqual(self.mailed("reg_received"), {"leitung", "vertretung", "admin"})

    def test_registrations_close_together_share_one_mail(self):
        session = self.session(mode="opt_in")
        self.change(session, self.mia, "registered")
        self.change(session, self.ole, "registered")
        item = InboxItem.objects.get(kind="reg_received")
        self.assertEqual(item.count, 2)
        self.assertTrue(item.title.startswith("2 Anmeldungen"))
        self.assertEqual(deliver_emails(now=later()), 3)  # one per recipient
        body = next(m.body for m in mail.outbox if m.to == ["leitung@example.invalid"])
        self.assertIn("Mia Test", body)
        self.assertIn("Ole Test", body)
        self.assertIn("2 angemeldet", body)

    def test_application_opens_one_task_until_assignment_is_published(self):
        session = self.session(mode="assignment", max_participants=1)
        self.change(session, self.mia, "applied")
        self.change(session, self.ole, "applied")
        task = InboxItem.objects.get(kind="reg_received")
        self.assertEqual((task.item_type, task.task_state), ("task", "open"))
        self.assertIn("2 offen", task.title)
        board = assignment.board(session, service.participation_for(session)[0])
        board = assignment.save_draft(session.pk, {str(self.mia.pk): "extra"}, board["revision"])
        with self.captureOnCommitCallbacks(execute=True):
            assignment.publish(session.pk, board["revision"], actor=self.lead)
        task.refresh_from_db()
        self.assertEqual((task.task_state, task.done_by), ("done", self.lead))
        # A later application opens a new task.
        ben = make_member(self.dept, "Ben", self.group)
        self.change(session, ben, "applied", actor=self.lead, source="staff")
        self.assertEqual(InboxItem.objects.filter(kind="reg_received", task_state="open").count(), 1)

    def test_withdrawing_the_last_application_completes_the_task(self):
        session = self.session(mode="assignment")
        self.change(session, self.mia, "applied")
        self.change(session, self.mia, "withdrawn")
        self.assertEqual(InboxItem.objects.get(kind="reg_received").task_state, "done")
        self.assertIn("vertretung", self.mailed("reg_cancelled"))

    def test_staff_recording_on_paper_does_not_mail_themselves(self):
        session = self.session(mode="assignment")
        self.change(session, self.mia, "applied", actor=self.lead, source="staff")
        self.assertEqual(self.mailed("reg_received"), {"vertretung", "admin"})
        delivery = EmailDelivery.objects.get(kind="reg_received", user=self.deputy)
        self.assertTrue(delivery.context["entries"][0]["by_staff"])
        self.assertIn(
            self.lead.pk, InboxRecipient.objects.filter(item__kind="reg_received").values_list("user_id", flat=True)
        )

    def test_cancellation_mail_does_not_wait_for_short_notice(self):
        session = self.session(mode="opt_in")
        self.change(session, self.mia, "registered")
        self.change(session, self.mia, "cancelled", reason_category="krankheit")
        self.assertEqual(self.mailed("reg_cancelled"), {"leitung", "vertretung", "admin"})
        deliver_emails(now=later())
        body = next(m.body for m in mail.outbox if m.subject.startswith("Abmeldung"))
        self.assertIn("Krankheit", body)

    def test_system_promotion_is_not_a_new_registration(self):
        session = self.session(mode="opt_in", max_participants=1)
        self.change(session, self.mia, "registered")
        self.change(session, self.ole, "registered")  # waitlisted: still a registration
        EmailDelivery.objects.all().delete()
        self.change(session, self.mia, "cancelled")
        self.assertFalse(EmailDelivery.objects.filter(kind="reg_received").exists())

    def test_staff_can_record_an_application_via_the_api(self):
        session = self.session(mode="assignment")
        path = f"/api/v1/participation/sessions/{session.pk}/registrations/{self.mia.pk}/"
        foreign = APIClient()
        foreign.force_login(self.foreign)
        self.assertEqual(foreign.put(path, {"target": "applied"}, format="json").status_code, 403)
        client = APIClient()
        client.force_login(self.lead)
        with self.captureOnCommitCallbacks(execute=True):
            response = client.put(path, {"target": "applied"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()["state"], response.json()["registration"]["source"]), ("applied", "staff"))
        self.assertTrue(InboxItem.objects.filter(kind="reg_received", item_type="task").exists())
