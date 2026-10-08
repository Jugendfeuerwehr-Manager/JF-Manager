from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.models import Department, RoleTemplate, UserDepartmentRole
from departments.role_comparison import compare_role_template


class RoleTemplateReadApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.template = RoleTemplate.objects.get(key="youth_leader")
        cls.view_permission = Permission.objects.get(
            content_type__app_label="departments", codename="view_roletemplate"
        )
        cls.admin = get_user_model().objects.create_user(username="role-read-admin")
        cls.admin.user_permissions.add(cls.view_permission)
        cls.editor = get_user_model().objects.create_user(username="role-edit-admin")
        cls.editor.user_permissions.add(
            cls.view_permission,
            Permission.objects.get(content_type__app_label="departments", codename="change_roletemplate"),
            Permission.objects.get(content_type__app_label="departments", codename="add_roletemplate"),
            Permission.objects.get(content_type__app_label="auth", codename="change_group"),
            Permission.objects.get(content_type__app_label="auth", codename="add_group"),
        )
        cls.staff = get_user_model().objects.create_user(username="role-read-staff", is_staff=True)
        cls.department_user = get_user_model().objects.create_user(username="role-read-dept")
        cls.department = Department.objects.create(name="Nord", code="role-read-nord")
        cls.department_group = Group.objects.create(name="Department role readers")
        cls.department_group.permissions.add(cls.view_permission)
        role = UserDepartmentRole.objects.create(user=cls.department_user, department=cls.department)
        role.groups.add(cls.department_group)

    def test_list_and_detail_require_global_explicit_role_view_permission(self):
        url = "/api/v1/admin/role-templates/"
        self.client.force_authenticate(user=self.staff)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(user=self.department_user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        rows = response.data.get("results", response.data)
        self.assertEqual(len(rows), 16)
        detail = self.client.get(f"{url}{self.template.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["key"], "youth_leader")
        self.assertEqual(detail.data["group"]["id"], self.template.group_id)

    def test_compare_shows_permission_diff_counts_and_fingerprint(self):
        self.client.force_authenticate(user=self.admin)
        url = f"/api/v1/admin/role-templates/{self.template.pk}/compare/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["missing_permissions"], [])
        self.assertEqual(response.data["extra_permissions"], [])
        self.assertIn("training.can_manage_training", response.data["actual_permissions"])
        self.assertEqual(len(response.data["fingerprint"]), 64)
        self.assertEqual(response.data["assignment_counts"]["global_users"], 0)

        permission = Permission.objects.get(content_type__app_label="members", codename="export_memberlist")
        self.template.group.permissions.add(permission)
        changed = self.client.get(url)
        self.assertEqual(changed.data["extra_permissions"], ["members.export_memberlist"])
        self.assertNotEqual(changed.data["fingerprint"], response.data["fingerprint"])

    def test_custom_template_has_no_catalog_expected_set(self):
        custom = RoleTemplate.objects.create(key="custom_role", name="Eigene Rolle", scope="department")
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"/api/v1/admin/role-templates/{custom.pk}/compare/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["group"])
        self.assertIsNone(response.data["expected_permissions"])
        self.assertIsNone(response.data["missing_permissions"])

    def test_read_api_does_not_accept_mutations(self):
        self.client.force_authenticate(user=self.admin)
        url = f"/api/v1/admin/role-templates/{self.template.pk}/"
        response = self.client.patch(url, {"name": "Changed"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "Jugendleiter")

    def test_metadata_patch_requires_current_fingerprint_and_cannot_change_key_or_scope(self):
        self.client.force_authenticate(user=self.editor)
        url = f"/api/v1/admin/role-templates/{self.template.pk}/"
        old = compare_role_template(self.template)["fingerprint"]
        forbidden = self.client.patch(url, {"fingerprint": old, "scope": "organization"}, format="json")
        self.assertEqual(forbidden.status_code, 400)
        changed = self.client.patch(url, {"fingerprint": old, "name": "Neue Anzeige"}, format="json")
        self.assertEqual(changed.status_code, 200)
        self.template.refresh_from_db()
        self.assertEqual(self.template.key, "youth_leader")
        self.assertEqual(self.template.scope, "department")
        self.assertEqual(self.template.name, "Neue Anzeige")
        stale = self.client.patch(url, {"fingerprint": old, "name": "Veraltet"}, format="json")
        self.assertEqual(stale.status_code, 409)

    def test_permission_change_requires_change_group_and_preserves_scope(self):
        url = f"/api/v1/admin/role-templates/{self.template.pk}/apply-permissions/"
        fingerprint = compare_role_template(self.template)["fingerprint"]
        names = compare_role_template(self.template)["actual_permissions"]
        self.client.force_authenticate(user=self.admin)
        self.assertEqual(
            self.client.post(url, {"fingerprint": fingerprint, "permissions": names}, format="json").status_code,
            403,
        )
        self.client.force_authenticate(user=self.editor)
        missing_fingerprint = self.client.post(url, {"permissions": names}, format="json")
        self.assertEqual(missing_fingerprint.status_code, 400)
        invalid = self.client.post(
            url,
            {"fingerprint": fingerprint, "permissions": [*names, "departments.can_access_all_departments"]},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(compare_role_template(self.template)["actual_permissions"], names)
        updated = self.client.post(
            url,
            {"fingerprint": fingerprint, "permissions": [*names, "members.export_memberlist"]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertIn("members.export_memberlist", updated.data["extra_permissions"])
        self.assertNotEqual(updated.data["fingerprint"], fingerprint)
        stale = self.client.post(url, {"fingerprint": fingerprint, "permissions": names}, format="json")
        self.assertEqual(stale.status_code, 409)

    def test_admin_cannot_change_own_group(self):
        self.template.group.user_set.add(self.editor)
        self.client.force_authenticate(user=self.editor)
        fingerprint = compare_role_template(self.template)["fingerprint"]
        response = self.client.post(
            f"/api/v1/admin/role-templates/{self.template.pk}/apply-permissions/",
            {"fingerprint": fingerprint, "permissions": compare_role_template(self.template)["actual_permissions"]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_archive_keeps_existing_group_rights(self):
        self.client.force_authenticate(user=self.editor)
        url = f"/api/v1/admin/role-templates/{self.template.pk}/archive/"
        old_permissions = set(self.template.group.permissions.values_list("pk", flat=True))
        fingerprint = compare_role_template(self.template)["fingerprint"]
        response = self.client.post(url, {"fingerprint": fingerprint}, format="json")
        self.assertEqual(response.status_code, 200)
        self.template.refresh_from_db()
        self.assertTrue(self.template.is_archived)
        self.assertEqual(set(self.template.group.permissions.values_list("pk", flat=True)), old_permissions)
        patch = self.client.patch(
            f"/api/v1/admin/role-templates/{self.template.pk}/",
            {"fingerprint": compare_role_template(self.template)["fingerprint"], "name": "Should fail"},
            format="json",
        )
        self.assertEqual(patch.status_code, 400)

    def test_duplicate_creates_unassigned_group_and_rolls_back_invalid_key(self):
        self.client.force_authenticate(user=self.editor)
        url = f"/api/v1/admin/role-templates/{self.template.pk}/duplicate/"
        fingerprint = compare_role_template(self.template)["fingerprint"]
        invalid = self.client.post(url, {"fingerprint": fingerprint, "key": "Bad-Key", "name": "Bad"}, format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(Group.objects.filter(name="jf_role__Bad-Key").exists())
        response = self.client.post(
            url,
            {"fingerprint": fingerprint, "key": "new_custom_role", "name": "Neue Rolle"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        duplicate = RoleTemplate.objects.get(key="new_custom_role")
        self.assertEqual(duplicate.scope, self.template.scope)
        self.assertFalse(duplicate.is_delegable)
        self.assertEqual(
            set(duplicate.group.permissions.values_list("pk", flat=True)),
            set(self.template.group.permissions.values_list("pk", flat=True)),
        )
        self.assertFalse(duplicate.group.user_set.exists())
        self.assertFalse(duplicate.group.department_assignments.exists())
