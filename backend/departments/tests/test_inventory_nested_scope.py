"""Linked inventory reads must retain the item's owner scope."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from inventory.models import Category, Item, ItemVariant


class InventoryNestedScopeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        department_a = Department.objects.create(name="A", code="nested-inventory-a")
        department_b = Department.objects.create(name="B", code="nested-inventory-b")
        cls.category = Category.objects.create(name="Shared category")
        cls.item_a = Item.objects.create(name="A tent", category=cls.category, department=department_a)
        cls.item_b = Item.objects.create(name="B tent", category=cls.category, department=department_b)
        cls.central_item = Item.objects.create(name="Central jacket", category=cls.category)
        cls.variant_a = ItemVariant.objects.create(parent_item=cls.item_a, variant_attributes={"size": "A"})
        cls.variant_b = ItemVariant.objects.create(parent_item=cls.item_b, variant_attributes={"size": "B"})
        cls.central_variant = ItemVariant.objects.create(
            parent_item=cls.central_item, variant_attributes={"size": "C"}
        )
        cls.viewer = get_user_model().objects.create_user(username="nested-inventory-viewer")
        group_a = Group.objects.create(name="Nested inventory viewer A")
        for codename in ("view_category", "view_item", "view_itemvariant"):
            group_a.permissions.add(
                Permission.objects.get(content_type__app_label="inventory", codename=codename)
            )
        UserDepartmentRole.objects.create(user=cls.viewer, department=department_a).groups.add(group_a)
        UserDepartmentRole.objects.create(user=cls.viewer, department=department_b)

    def setUp(self):
        self.client.force_authenticate(user=self.viewer)

    def test_variant_list_shows_own_and_central_but_not_other_department(self):
        response = self.client.get("/api/v1/inventory/variants/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual({row["id"] for row in rows}, {self.variant_a.pk, self.central_variant.pk})

    def test_other_department_variant_detail_is_hidden(self):
        response = self.client.get(f"/api/v1/inventory/variants/{self.variant_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_category_items_show_own_and_central_but_not_other_department(self):
        response = self.client.get(f"/api/v1/inventory/categories/{self.category.pk}/items/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual({row["id"] for row in rows}, {self.item_a.pk, self.central_item.pk})

    def test_category_count_excludes_other_department_items(self):
        response = self.client.get(f"/api/v1/inventory/categories/{self.category.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["item_count"], 2)

    def test_variant_change_right_in_a_cannot_modify_b_variant(self):
        role_a = self.viewer.department_roles.get(department=self.item_a.department)
        role_a.groups.first().permissions.add(
            Permission.objects.get(content_type__app_label="inventory", codename="change_itemvariant")
        )

        response = self.client.patch(
            f"/api/v1/inventory/variants/{self.variant_b.pk}/", {"sku": "changed"}, format="json"
        )

        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.variant_b.refresh_from_db()
        self.assertEqual(self.variant_b.sku, "")

    def test_variant_change_right_in_a_allows_a_but_not_central_variant(self):
        role_a = self.viewer.department_roles.get(department=self.item_a.department)
        role_a.groups.first().permissions.add(
            Permission.objects.get(content_type__app_label="inventory", codename="change_itemvariant")
        )
        self.viewer.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))

        own = self.client.patch(
            f"/api/v1/inventory/variants/{self.variant_a.pk}/", {"sku": "own"}, format="json"
        )
        central = self.client.patch(
            f"/api/v1/inventory/variants/{self.central_variant.pk}/", {"sku": "central"}, format="json"
        )

        self.assertEqual(own.status_code, status.HTTP_200_OK, own.data)
        self.assertEqual(central.status_code, status.HTTP_403_FORBIDDEN)
        self.central_variant.refresh_from_db()
        self.assertEqual(self.central_variant.sku, "")
