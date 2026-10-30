"""UX-02.1: person pickers list real, active accounts only. Fictional data.

DSGVO: the directory only shows colleagues sharing a department with the
caller; portal accounts (parents, members) never appear.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole

User = get_user_model()


class UserPickerTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Mitte", code="picker-mitte")
        self.foreign = Department.objects.create(name="Nord", code="picker-nord")
        self.viewer = User.objects.create_user(username="viewer", password="Viewer!123")
        aktiv = User.objects.create_user(username="aktiv", password="Aktiv!1234")
        ehemalig = User.objects.create_user(username="ehemalig", password="Ehemalig!1", is_active=False)
        fremd = User.objects.create_user(username="fremd", password="Fremd!1234")
        User.objects.create_user(
            username="eltern@example.org", password="Eltern!123", account_kind=User.AccountKind.PORTAL
        )
        User.objects.create_user(username="ohne-rolle", password="Ohne!12345")
        User.objects.get_or_create(username="AnonymousUser")
        # Portal accounts cannot hold roles (portal.signals); they matter for org-wide scope.
        for user in (self.viewer, aktiv, ehemalig):
            UserDepartmentRole.objects.create(user=user, department=self.department)
        UserDepartmentRole.objects.create(user=fremd, department=self.foreign)
        self.client.force_authenticate(self.viewer)

    def usernames(self, query=""):
        response = self.client.get(f"/api/v1/users/{query}")
        self.assertEqual(response.status_code, 200)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        return {row["username"] for row in rows}

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get("/api/v1/users/").status_code, (401, 403))

    def test_active_filter_is_applied(self):
        names = self.usernames("?is_active=true&limit=1000")
        self.assertIn("aktiv", names)
        self.assertNotIn("ehemalig", names)

    def test_system_account_is_never_listed(self):
        self.assertNotIn("AnonymousUser", self.usernames())
        self.assertNotIn("AnonymousUser", self.usernames("?is_active=true"))

    def test_only_colleagues_of_own_departments_are_listed(self):
        self.assertEqual(self.usernames(), {"viewer", "aktiv", "ehemalig"})

    def test_foreign_department_accounts_are_hidden(self):
        fremd = User.objects.get(username="fremd")
        self.assertEqual(self.client.get(f"/api/v1/users/{fremd.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/users/?department={self.foreign.pk}").status_code, 403)

    def test_portal_accounts_are_never_listed(self):
        eltern = User.objects.get(username="eltern@example.org")
        self.assertNotIn("eltern@example.org", self.usernames())
        self.assertEqual(self.client.get(f"/api/v1/users/{eltern.pk}/").status_code, 404)

    def test_account_without_role_only_sees_itself(self):
        self.client.force_authenticate(User.objects.get(username="ohne-rolle"))
        self.assertEqual(self.usernames(), {"ohne-rolle"})

    def test_department_param_narrows_to_active_department(self):
        UserDepartmentRole.objects.create(user=self.viewer, department=self.foreign)
        self.assertEqual(self.usernames(f"?department={self.foreign.pk}"), {"viewer", "fremd"})

    def test_organisation_wide_scope_lists_all_staff_but_no_portal_accounts(self):
        self.viewer.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))
        self.viewer = User.objects.get(pk=self.viewer.pk)
        self.client.force_authenticate(self.viewer)
        names = self.usernames("?limit=1000")
        self.assertTrue({"aktiv", "fremd", "ohne-rolle"} <= names)
        self.assertNotIn("eltern@example.org", names)
