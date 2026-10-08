"""Acceptance against the installed catalog, using actual HTTP endpoints."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.models import Department, RoleTemplate, UserDepartmentRole
from inventory.models import Category, Item
from members.models import Member


class StandardRoleMatrixTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.a = Department.objects.create(name="Acceptance A", code="acceptance-a")
        cls.b = Department.objects.create(name="Acceptance B", code="acceptance-b")
        cls.member_a = Member.objects.create(name="Synthetic", lastname="A")
        cls.member_b = Member.objects.create(name="Synthetic", lastname="B")
        cls.member_a.departments.add(cls.a)
        cls.member_b.departments.add(cls.b)
        category = Category.objects.create(name="Acceptance")
        cls.item_a = Item.objects.create(name="Material A", category=category, department=cls.a)
        cls.item_b = Item.objects.create(name="Material B", category=category, department=cls.b)
        cls.central = Item.objects.create(name="Central", category=category)

    def account(self, key):
        user = get_user_model().objects.create_user(username=f"acceptance-{key}")
        template = RoleTemplate.objects.get(key=key)
        if template.scope == "organization":
            user.groups.add(template.group)
        else:
            UserDepartmentRole.objects.create(user=user, department=self.a).groups.add(template.group)
        self.client.force_authenticate(user)
        return user

    def test_profile_preserves_permission_namespaces_and_separate_scoped_rights(self):
        user = self.account("system_administrator")
        UserDepartmentRole.objects.create(user=user, department=self.a).groups.add(
            RoleTemplate.objects.get(key="youth_leader").group
        )
        response = self.client.get("/api/v1/users/me/")
        self.assertIn("auth.view_group", response.data["qualified_permissions"])
        self.assertNotIn("members.view_group", response.data["qualified_permissions"])
        self.assertIn("members.view_group", response.data["department_roles"][0]["qualified_permissions"])

    def test_all_sixteen_roles_have_only_their_expected_subject_modules(self):
        leadership = {"youth_director", "department_youth_director", "youth_leader"}
        members = leadership | {
            "supervisor",
            "email_communicator",
            "email_communicator_organization",
            "qualification_manager",
            "qualification_manager_organization",
        }
        training = leadership | {"supervisor", "training_planner", "training_planner_organization"}
        inventory = {
            "inventory_manager",
            "inventory_manager_organization",
            "order_manager",
            "order_manager_organization",
        }
        expected = {
            "members/": members,
            "parents/": leadership | {"supervisor"},
            "member-lists/": leadership,
            "servicebook/services/": leadership | {"supervisor"},
            "training/sessions/": training,
            "inventory/items/": inventory,
            "orders/": {"order_manager", "order_manager_organization"},
            "emails/": {"email_communicator", "email_communicator_organization"},
            "qualifications/": leadership | {"qualification_manager", "qualification_manager_organization"},
            "admin/users/": {"system_administrator"},
        }
        for template in RoleTemplate.objects.order_by("key"):
            self.account(template.key)
            for endpoint, keys in expected.items():
                with self.subTest(role=template.key, endpoint=endpoint):
                    response = self.client.get(f"/api/v1/{endpoint}")
                    self.assertEqual(response.status_code, 200 if template.key in keys else 403, response.data)

    def test_no_standard_role_implies_destructive_personal_data_permissions(self):
        for template in RoleTemplate.objects.order_by("key"):
            self.account(template.key)
            with self.subTest(role=template.key):
                self.assertEqual(self.client.delete(f"/api/v1/members/{self.member_a.pk}/").status_code, 403)
                self.assertFalse(template.group.permissions.filter(codename__startswith="delete_").exists())

    def test_department_roles_read_only_own_department_and_shared_catalog(self):
        for key, endpoint, own, foreign in (
            ("youth_leader", "members", self.member_a, self.member_b),
            ("inventory_manager", "inventory/items", self.item_a, self.item_b),
            ("order_manager", "inventory/items", self.item_a, self.item_b),
        ):
            self.account(key)
            with self.subTest(role=key):
                rows = self.client.get(f"/api/v1/{endpoint}/").data["results"]
                self.assertEqual(
                    {row["id"] for row in rows},
                    {own.pk} | ({self.central.pk} if endpoint == "inventory/items" else set()),
                )
                self.assertIn(self.client.get(f"/api/v1/{endpoint}/{foreign.pk}/").status_code, (403, 404))

    def test_combination_keeps_subject_rights_in_their_own_department(self):
        user = self.account("youth_leader")
        UserDepartmentRole.objects.create(user=user, department=self.b).groups.add(
            RoleTemplate.objects.get(key="inventory_manager").group
        )
        user.groups.add(RoleTemplate.objects.get(key="system_administrator").group)
        self.client.force_authenticate(get_user_model().objects.get(pk=user.pk))
        self.assertEqual({row["id"] for row in self.client.get("/api/v1/members/").data["results"]}, {self.member_a.pk})
        self.assertEqual(
            {row["id"] for row in self.client.get("/api/v1/inventory/items/").data["results"]},
            {self.item_b.pk, self.central.pk},
        )
        self.assertEqual(
            self.client.patch(f"/api/v1/members/{self.member_b.pk}/", {"name": "Denied"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/inventory/items/{self.item_a.pk}/", {"name": "Denied"}, format="json"
            ).status_code,
            403,
        )

    def test_organization_inventory_does_not_expand_department_member_access(self):
        user = self.account("supervisor")
        user.groups.add(RoleTemplate.objects.get(key="inventory_manager_organization").group)
        self.client.force_authenticate(get_user_model().objects.get(pk=user.pk))
        self.assertEqual({row["id"] for row in self.client.get("/api/v1/members/").data["results"]}, {self.member_a.pk})
        self.assertEqual(
            {row["id"] for row in self.client.get("/api/v1/inventory/items/").data["results"]},
            {self.item_a.pk, self.item_b.pk, self.central.pk},
        )
