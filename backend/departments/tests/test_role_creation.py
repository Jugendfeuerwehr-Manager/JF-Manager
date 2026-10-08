from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.models import RoleTemplate
from departments.role_comparison import compare_role_template


class RoleCreationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser(username="synthetic-role-creator")

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_create_from_readable_name_generates_unique_unassigned_roles(self):
        payload = {
            "name": "Eigene Betreuung",
            "scope": "department",
            "permissions": ["members.view_member"],
            "is_delegable": True,
        }
        roles = []
        for _ in range(2):
            response = self.client.post("/api/v1/admin/role-templates/", payload, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            role = RoleTemplate.objects.get(pk=response.data["id"])
            self.assertTrue(role.key.startswith("custom_eigene_betreuung_"))
            self.assertFalse(role.group.user_set.exists())
            self.assertFalse(role.group.department_assignments.exists())
            self.assertFalse(response.data["delegation_approved"])
            self.assertEqual(set(role.group.permissions.values_list("codename", flat=True)), {"view_member"})
            roles.append(role)
        self.assertNotEqual(roles[0].key, roles[1].key)

    def test_organization_role_adds_area_permission_but_no_subject_rights(self):
        response = self.client.post(
            "/api/v1/admin/role-templates/",
            {"name": "Organisation Test", "scope": "organization", "permissions": []},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            set(RoleTemplate.objects.get(pk=response.data["id"]).group.permissions.values_list("codename", flat=True)),
            {"can_access_all_departments"},
        )

    def test_invalid_creation_is_atomic_and_reserved_standard_keys_are_protected(self):
        groups = Group.objects.count()
        for changes in (
            {"permissions": ["members.missing_permission"]},
            {"permissions": ["departments.can_access_all_departments"]},
            {"key": "supervisor"},
            {"key": "Bad Key"},
            {"scope": "both"},
        ):
            payload = {"name": "Invalid synthetic", "scope": "department", "permissions": [], **changes}
            self.assertEqual(self.client.post("/api/v1/admin/role-templates/", payload, format="json").status_code, 400)
            self.assertEqual(Group.objects.count(), groups)

    def test_duplicate_without_technical_key_copies_rights_without_assignments_or_approval(self):
        source = RoleTemplate.objects.get(key="supervisor")
        response = self.client.post(
            f"/api/v1/admin/role-templates/{source.pk}/duplicate/",
            {"name": "Betreuung Kopie", "fingerprint": compare_role_template(source)["fingerprint"]},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        role = RoleTemplate.objects.get(pk=response.data["id"])
        self.assertEqual(
            set(role.group.permissions.values_list("pk", flat=True)),
            set(source.group.permissions.values_list("pk", flat=True)),
        )
        self.assertFalse(role.group.user_set.exists())
        self.assertFalse(role.delegation_approval)

    def test_ordinary_staff_cannot_create_roles(self):
        self.client.force_authenticate(
            get_user_model().objects.create_user(username="synthetic-ordinary-staff", is_staff=True)
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/admin/role-templates/", {"name": "Denied", "scope": "department"}, format="json"
            ).status_code,
            403,
        )
