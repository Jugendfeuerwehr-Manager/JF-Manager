from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.models import Department, RoleTemplate, UserDepartmentRole


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
        self.assertEqual(response.status_code, 405)
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "Jugendleiter")
