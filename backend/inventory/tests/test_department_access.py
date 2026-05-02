from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from inventory.models import Category, Item, Stock, StorageLocation


class InventoryDepartmentAccessTest(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="dept_user", password="pw12345")

        self.dept_a = Department.objects.create(name="Abteilung A", code="dept-a")
        self.dept_b = Department.objects.create(name="Abteilung B", code="dept-b")

        permissions = Permission.objects.filter(
            codename__in=[
                "view_item",
                "view_storagelocation",
                "add_transaction",
                "view_stock",
                "view_transaction",
            ]
        )
        group = Group.objects.create(name="inventory-dept-role")
        group.permissions.set(permissions)

        role = UserDepartmentRole.objects.create(user=self.user, department=self.dept_a)
        role.groups.add(group)

        self.category = Category.objects.create(name="Kategorie")

        self.item_dept_a = Item.objects.create(name="Item A", category=self.category, department=self.dept_a)
        self.item_dept_b = Item.objects.create(name="Item B", category=self.category, department=self.dept_b)
        self.item_central = Item.objects.create(name="Item Zentral", category=self.category, department=None)

        self.location_dept_a = StorageLocation.objects.create(name="Lager A", department=self.dept_a)
        self.location_dept_b = StorageLocation.objects.create(name="Lager B", department=self.dept_b)
        self.location_central = StorageLocation.objects.create(name="Lager Zentral", department=None)

        Stock.objects.create(item=self.item_dept_a, location=self.location_dept_a, quantity=10)
        Stock.objects.create(item=self.item_dept_b, location=self.location_dept_b, quantity=10)
        Stock.objects.create(item=self.item_central, location=self.location_central, quantity=10)

        self.client.force_authenticate(user=self.user)

    def test_items_include_own_and_central_departments_only(self):
        response = self.client.get("/api/v1/inventory/items/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {entry["name"] for entry in response.data["results"]}
        self.assertIn(self.item_dept_a.name, names)
        self.assertIn(self.item_central.name, names)
        self.assertNotIn(self.item_dept_b.name, names)

    def test_items_with_department_param_still_include_central_records(self):
        response = self.client.get(f"/api/v1/inventory/items/?department={self.dept_a.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {entry["name"] for entry in response.data["results"]}
        self.assertIn(self.item_dept_a.name, names)
        self.assertIn(self.item_central.name, names)
        self.assertNotIn(self.item_dept_b.name, names)

    def test_locations_with_department_param_still_include_central_records(self):
        response = self.client.get(f"/api/v1/inventory/locations/?department={self.dept_a.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {entry["name"] for entry in response.data["results"]}
        self.assertIn(self.location_dept_a.name, names)
        self.assertIn(self.location_central.name, names)
        self.assertNotIn(self.location_dept_b.name, names)

    def test_stocks_include_own_and_central_departments_only(self):
        response = self.client.get("/api/v1/inventory/stocks/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {entry["item_name"] for entry in response.data["results"]}
        self.assertIn(self.item_dept_a.name, names)
        self.assertIn(self.item_central.name, names)
        self.assertNotIn(self.item_dept_b.name, names)

    def test_stocks_with_department_param_still_include_central_records(self):
        response = self.client.get(f"/api/v1/inventory/stocks/?department={self.dept_a.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {entry["item_name"] for entry in response.data["results"]}
        self.assertIn(self.item_dept_a.name, names)
        self.assertIn(self.item_central.name, names)
        self.assertNotIn(self.item_dept_b.name, names)

    def test_transaction_for_foreign_department_item_is_rejected(self):
        response = self.client.post(
            "/api/v1/inventory/transactions/",
            {
                "transaction_type": "OUT",
                "item": self.item_dept_b.id,
                "source": self.location_dept_b.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("item", response.data)

    def test_transaction_with_foreign_target_location_is_rejected(self):
        response = self.client.post(
            "/api/v1/inventory/transactions/",
            {
                "transaction_type": "MOVE",
                "item": self.item_dept_a.id,
                "source": self.location_dept_a.id,
                "target": self.location_dept_b.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("target", response.data)
