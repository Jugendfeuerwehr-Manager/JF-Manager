"""NOTIF-01.1/01.2: inbox recipients, bundling, team status, re-check and portal notices."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from notifications.inbox import complete_tasks, notify, purge, staff_with_permission
from notifications.models import InboxItem, InboxRecipient

User = get_user_model()
PERM = "portal.invite_portal_account"


class InboxTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.nord = Department.objects.create(name="Nord")
        cls.group = Group.objects.create(name="Portalverwaltung")
        cls.group.permissions.add(Permission.objects.get(codename="invite_portal_account"))
        cls.anna = cls.role_user("anna", cls.mitte)
        cls.ben = cls.role_user("ben", cls.mitte)
        cls.nils = cls.role_user("nils", cls.nord)

    @classmethod
    def role_user(cls, name, department):
        user = User.objects.create_user(name, password="x", first_name=name.title())
        UserDepartmentRole.objects.create(user=user, department=department).groups.add(cls.group)
        return user

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client


class RecipientTests(InboxTestBase):
    def test_department_roles_global_rights_and_portal_accounts(self):
        global_assigned = User.objects.create_user("glob", password="x")
        global_assigned.groups.add(self.group)
        UserDepartmentRole.objects.create(user=global_assigned, department=self.mitte)
        global_unassigned = User.objects.create_user("frei", password="x")
        global_unassigned.groups.add(self.group)
        inactive = self.role_user("weg", self.mitte)
        User.objects.filter(pk=inactive.pk).update(is_active=False)
        User.objects.create_user("p@example.invalid", password="x", account_kind="portal")
        names = set(staff_with_permission(PERM, self.mitte.pk).values_list("username", flat=True))
        self.assertEqual(names, {"anna", "ben", "glob"})


class BundlingAndStatusTests(InboxTestBase):
    def test_notices_are_bundled_and_marked_unread_again(self):
        first = notify(
            kind="reg_cancelled",
            category="registrations",
            title="1 Abmeldung",
            department=self.mitte,
            permission=PERM,
            group_key="reg_cancelled:session:1",
        )
        InboxRecipient.objects.filter(item=first, user=self.anna).update(read_at=timezone.now())
        second = notify(
            kind="reg_cancelled",
            category="registrations",
            title="2 Abmeldungen",
            department=self.mitte,
            permission=PERM,
            group_key="reg_cancelled:session:1",
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual((second.count, second.title), (2, "2 Abmeldungen"))
        self.assertFalse(InboxRecipient.objects.filter(item=first, read_at__isnull=False).exists())
        self.assertEqual(InboxItem.objects.count(), 1)

    def test_team_status_and_automatic_completion(self):
        task = notify(
            kind="cr_submitted",
            category="requests",
            title="Antrag prüfen",
            item_type="task",
            department=self.mitte,
            permission=PERM,
            obj=self.mitte,
        )
        response = self.client_for(self.anna).post(f"/api/v1/notifications/inbox/{task.pk}/done/")
        self.assertEqual((response.json()["task_state"], response.json()["done_by"]), ("done", "Anna"))
        ben_view = self.client_for(self.ben).get("/api/v1/notifications/inbox/?done=1").json()["results"][0]
        self.assertEqual((ben_view["task_state"], ben_view["done_by"], ben_view["done_via"]), ("done", "Anna", "ui"))
        other = notify(
            kind="cr_submitted",
            category="requests",
            title="Antrag prüfen",
            item_type="task",
            department=self.mitte,
            permission=PERM,
            obj=self.nord,
        )
        self.assertEqual(complete_tasks(self.nord), 1)
        other.refresh_from_db()
        self.assertEqual((other.task_state, other.done_via), ("done", "auto"))
        self.assertEqual(self.client_for(self.ben).get("/api/v1/notifications/inbox/").json()["count"], 0)


class InboxApiTests(InboxTestBase):
    def test_scope_counts_read_and_recheck(self):
        notify(
            kind="reg_cancelled",
            category="registrations",
            title="Abmeldung Mitte",
            department=self.mitte,
            permission=PERM,
        )
        task = notify(
            kind="slot_free_manual",
            category="staffing",
            title="Platz frei",
            item_type="task",
            department=self.mitte,
            permission=PERM,
        )
        notify(
            kind="reg_cancelled",
            category="registrations",
            title="Abmeldung Nord",
            department=self.nord,
            permission=PERM,
        )
        anna = self.client_for(self.anna)
        counts = anna.get("/api/v1/notifications/inbox/counts/").json()
        self.assertEqual(
            {k: counts[k] for k in ("open_tasks", "unread_notices", "total")},
            {"open_tasks": 1, "unread_notices": 1, "total": 2},
        )
        titles = [r["title"] for r in anna.get("/api/v1/notifications/inbox/").json()["results"]]
        self.assertEqual(sorted(titles), ["Abmeldung Mitte", "Platz frei"])
        self.assertEqual(
            [r["title"] for r in anna.get("/api/v1/notifications/inbox/?type=task").json()["results"]], ["Platz frei"]
        )
        anna.post(
            "/api/v1/notifications/inbox/read-bulk/", {"ids": [i.pk for i in InboxItem.objects.all()]}, format="json"
        )
        self.assertEqual(anna.get("/api/v1/notifications/inbox/counts/").json()["unread_notices"], 0)
        # Withdrawn rights hide the entries again (4.9.2).
        UserDepartmentRole.objects.filter(user=self.anna).delete()
        self.assertEqual(anna.get("/api/v1/notifications/inbox/").json()["count"], 0)
        self.assertEqual(anna.post(f"/api/v1/notifications/inbox/{task.pk}/done/").status_code, 404)

    def test_portal_accounts_only_see_personal_notices(self):
        portal = User.objects.create_user("p@example.invalid", password="x", account_kind="portal")
        notify(kind="waitlist_promoted", category="participation", title="Mila ist nachgerückt", recipients=[portal])
        notify(
            kind="reg_cancelled",
            category="registrations",
            title="Team",
            department=self.mitte,
            permission=PERM,
            recipients=[portal],
        )
        browser = self.client_class()
        browser.force_login(portal)
        data = browser.get("/api/v1/portal/notifications/").json()
        self.assertEqual([r["title"] for r in data["results"]], ["Mila ist nachgerückt"])
        self.assertEqual(data["unread"], 1)
        self.assertEqual(browser.get("/api/v1/notifications/inbox/").status_code, 403)


class RetentionTests(InboxTestBase):
    def test_purge_after_180_days(self):
        old = timezone.now() - timedelta(days=181)
        task = notify(
            kind="x", category="staffing", title="Alt", item_type="task", department=self.mitte, permission=PERM
        )
        InboxItem.objects.filter(pk=task.pk).update(task_state="done", done_at=old)
        notice = notify(kind="y", category="registrations", title="Gelesen", department=self.mitte, permission=PERM)
        InboxItem.objects.filter(pk=notice.pk).update(updated_at=old)
        InboxRecipient.objects.filter(item=notice).update(read_at=old)
        unread = notify(kind="z", category="registrations", title="Ungelesen", department=self.mitte, permission=PERM)
        InboxItem.objects.filter(pk=unread.pk).update(updated_at=old)
        self.assertEqual(purge(), 2)
        self.assertEqual(list(InboxItem.objects.values_list("title", flat=True)), ["Ungelesen"])
        call_command("purge_inbox", stdout=__import__("io").StringIO())
