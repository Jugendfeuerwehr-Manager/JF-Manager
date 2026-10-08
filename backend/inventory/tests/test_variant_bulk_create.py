from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from inventory.models import Category, Item, ItemVariant

URL = "/api/v1/inventory/variants/bulk-create/"


class ItemVariantBulkCreateTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="variant_user", password="pw12345")
        self.dept_a = Department.objects.create(name="Abteilung A", code="dept-a")
        self.dept_b = Department.objects.create(name="Abteilung B", code="dept-b")

        group = Group.objects.create(name="inventory-variant-role")
        group.permissions.set(
            Permission.objects.filter(codename__in=["view_item", "view_itemvariant", "add_itemvariant"])
        )
        role = UserDepartmentRole.objects.create(user=self.user, department=self.dept_a)
        role.groups.add(group)

        category = Category.objects.create(name="Bekleidung")
        self.item_a = Item.objects.create(name="T-Shirt", category=category, department=self.dept_a)
        self.item_b = Item.objects.create(name="Hose", category=category, department=self.dept_b)
        self.client.force_authenticate(user=self.user)

    def test_creates_one_variant_per_value_and_marks_parent(self):
        response = self.client.post(
            URL,
            {"parent_item": self.item_a.id, "attribute": "Größe", "values": ["S", "M", " L ", "m", ""]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual([v["variant_attributes"]["Größe"] for v in response.data["created"]], ["S", "M", "L"])
        self.assertEqual(response.data["skipped"], [])
        self.item_a.refresh_from_db()
        self.assertTrue(self.item_a.is_variant_parent)

    def test_skips_existing_values(self):
        ItemVariant.objects.create(parent_item=self.item_a, variant_attributes={"Größe": "M"})

        response = self.client.post(
            URL, {"parent_item": self.item_a.id, "attribute": "Größe", "values": ["S", "m", "L"]}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["skipped"], ["m"])
        self.assertEqual(self.item_a.variants.count(), 3)

    def test_rejects_item_of_other_department_without_changes(self):
        response = self.client.post(
            URL, {"parent_item": self.item_b.id, "attribute": "Größe", "values": ["S", "M"]}, format="json"
        )

        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.assertFalse(self.item_b.variants.exists())

    def test_rejects_empty_values(self):
        response = self.client.post(
            URL, {"parent_item": self.item_a.id, "attribute": "Größe", "values": [" ", ""]}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.item_a.variants.exists())
