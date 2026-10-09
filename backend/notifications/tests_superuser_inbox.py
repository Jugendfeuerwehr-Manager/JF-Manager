"""UX-10.1: superusers in the team inbox, quiet channels by default, counts by category."""

import importlib
from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone

from departments.models import UserDepartmentRole
from notifications.dispatch import queue_email, wants
from notifications.inbox import notify, staff_with_permission
from notifications.models import EmailDelivery, InboxItem, InboxRecipient, NotificationPreference
from notifications.tests_inbox import PERM, InboxTestBase

User = get_user_model()
COUNTS = "/api/v1/notifications/inbox/counts/"


def team_item(department, kind="a", category="requests", item_type="notice", title="T"):
    return notify(
        kind=kind, category=category, title=title, item_type=item_type, department=department, permission=PERM
    )


class SuperuserInboxTests(InboxTestBase):
    def setUp(self):
        self.root = User.objects.create_superuser("root", "root@example.org", "x")

    def test_superuser_is_addressed_for_any_department(self):
        self.assertIn(self.root, staff_with_permission(PERM, self.mitte.pk))
        self.assertIn(self.root, staff_with_permission(PERM, self.nord.pk))
        self.assertIn(self.root, staff_with_permission(PERM, None))

    def test_inactive_superusers_are_not_addressed(self):
        User.objects.create_superuser("alt", "alt@example.org", "x", is_active=False)
        users = set(staff_with_permission(PERM, self.mitte.pk))
        self.assertEqual({u.username for u in users if u.is_superuser}, {"root"})

    def test_superuser_counts_team_task(self):
        team_item(self.mitte, item_type="task")
        body = self.client_for(self.root).get(COUNTS).json()
        self.assertEqual(body["open_tasks"], 1)
        self.assertEqual(body["by_category"]["requests"], 1)

    def test_staff_without_right_or_in_other_department_still_gets_nothing(self):
        outsider = User.objects.create_user("aussen", password="x")
        item = team_item(self.mitte, item_type="task")
        recipients = set(InboxRecipient.objects.filter(item=item).values_list("user__username", flat=True))
        self.assertNotIn("aussen", recipients)
        self.assertNotIn("nils", recipients)
        self.assertEqual(self.client_for(outsider).get(COUNTS).json()["total"], 0)

    def test_superuser_with_a_real_role_keeps_mail_by_default(self):
        UserDepartmentRole.objects.create(user=self.root, department=self.mitte).groups.add(self.group)
        self.assertTrue(wants(self.root, "cr_submitted", "email", explicit=False))
        self.assertTrue(queue_email("cr_submitted", self.root, {}, event_key="role:1"))

    def test_superuser_gets_no_mail_by_default_but_with_opt_in(self):
        self.assertFalse(wants(self.root, "cr_submitted", "email", explicit=False))
        self.assertIsNone(queue_email("cr_submitted", self.root, {}, event_key="a:1"))
        self.assertEqual(EmailDelivery.objects.count(), 0)
        NotificationPreference.objects.create(user=self.root, kind="cr_submitted", email=True, push=False)
        self.assertTrue(wants(self.root, "cr_submitted", "email", explicit=False))
        self.assertTrue(queue_email("cr_submitted", self.root, {}, event_key="a:2"))
        self.assertFalse(wants(self.root, "cr_submitted", "push", explicit=False))

    def test_explicitly_responsible_superuser_keeps_default_mail(self):
        self.assertTrue(queue_email("reg_cancelled", self.root, {}, event_key="a:3", explicit=True))

    def test_regular_staff_keeps_default_on_and_preferences_show_superuser_default(self):
        self.assertTrue(wants(self.anna, "cr_submitted", "email"))
        rows = self.client_for(self.root).get("/api/v1/notifications/preferences/").json()
        self.assertTrue(rows and all(not r["email"] and not r["push"] for r in rows))


class CountsByCategoryTests(InboxTestBase):
    def test_zero_filled_and_counts_open_tasks_and_unread_notices(self):
        team_item(self.mitte, "a", "requests", "task")
        team_item(self.mitte, "b", "registrations")
        read = team_item(self.mitte, "c", "registrations")
        InboxRecipient.objects.filter(item=read, user=self.anna).update(read_at=timezone.now())
        done = team_item(self.mitte, "d", "requests", "task")
        InboxItem.objects.filter(pk=done.pk).update(task_state="done")
        body = self.client_for(self.anna).get(COUNTS).json()
        self.assertEqual(set(body["by_category"]), set(InboxItem.Category.values))
        self.assertEqual(body["by_category"]["requests"], 1)
        self.assertEqual(body["by_category"]["registrations"], 1)
        self.assertEqual(body["by_category"]["staffing"], 0)
        self.assertEqual(body["total"], 2)
        self.assertEqual((body["open_tasks"], body["unread_notices"]), (1, 1))

    def test_respects_department_visibility(self):
        team_item(self.mitte, item_type="task")
        body = self.client_for(self.nils).get(COUNTS).json()
        self.assertEqual(body["by_category"]["requests"], 0)
        self.assertEqual(body["total"], 0)


class BackfillTests(InboxTestBase):
    def test_backfill_adds_superusers_to_open_tasks_and_recent_notices_only(self):
        root = User.objects.create_superuser("root", "root@example.org", "x")
        User.objects.create_superuser("alt", "alt@example.org", "x", is_active=False)
        task = team_item(self.mitte, "a", "requests", "task")
        done = team_item(self.mitte, "d", "requests", "task")
        recent = team_item(self.mitte, "b", "staffing")
        old = team_item(self.mitte, "c", "staffing")
        personal = notify(kind="p", category="participation", title="P", recipients=[self.anna])
        InboxItem.objects.filter(pk=done.pk).update(task_state="done")
        InboxItem.objects.filter(pk=old.pk).update(updated_at=timezone.now() - timedelta(days=45))
        InboxRecipient.objects.filter(user=root).delete()
        migration = importlib.import_module("notifications.migrations.0004_superuser_inbox_backfill")
        self.assertEqual(migration.backfill(apps, None), 2)
        have = set(InboxRecipient.objects.filter(user=root).values_list("item_id", flat=True))
        self.assertEqual(have, {task.pk, recent.pk})
        self.assertNotIn(personal.pk, have)
        self.assertEqual(migration.backfill(apps, None), 0)  # idempotent
