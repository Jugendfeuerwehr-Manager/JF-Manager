"""A central wardrobe can lend to department members with explicit global rights."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from inventory.models import Category, Item, Stock, StorageLocation, Transaction
from members.models import Member


class CentralInventoryRoleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="A", code="central-wardrobe-a")
        cls.member = Member.objects.create(name="A", lastname="Member")
        cls.member.departments.add(cls.department)
        category = Category.objects.create(name="Clothing")
        cls.central_item = Item.objects.create(name="Central jacket", category=category, department=None)
        cls.central_location = StorageLocation.objects.create(name="Central wardrobe", department=None)
        Stock.objects.create(item=cls.central_item, location=cls.central_location, quantity=3)

        cls.global_manager = get_user_model().objects.create_user(
            username="central-wardrobe-manager", password="test-only-password"
        )
        cls.global_manager.user_permissions.add(
            Permission.objects.get(codename="can_access_all_departments"),
            Permission.objects.get(content_type__app_label="inventory", codename="add_transaction"),
        )

        cls.scoped_manager = get_user_model().objects.create_user(
            username="scoped-wardrobe-manager", password="test-only-password"
        )
        cls.scoped_manager.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))
        group = Group.objects.create(name="Inventory transaction creator A")
        group.permissions.add(Permission.objects.get(content_type__app_label="inventory", codename="add_transaction"))
        UserDepartmentRole.objects.create(user=cls.scoped_manager, department=cls.department).groups.add(group)

    def _lend_central_jacket(self):
        return self.client.post(
            "/api/v1/inventory/transactions/batch-loan/",
            {"member": self.member.pk, "items": [{"item": self.central_item.pk, "quantity": 1}]},
            format="json",
        )

    def test_global_inventory_manager_can_lend_central_item_to_department_member(self):
        self.client.force_authenticate(user=self.global_manager)

        response = self._lend_central_jacket()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Transaction.objects.filter(transaction_type="LOAN", item=self.central_item).count(), 1)
        self.assertEqual(Stock.objects.get(item=self.central_item, location=self.central_location).quantity, 2)
        self.assertEqual(self.member.personal_storage_location.department_id, self.department.pk)

    def test_org_scope_with_only_department_transaction_right_cannot_lend_central_item(self):
        self.client.force_authenticate(user=self.scoped_manager)

        response = self._lend_central_jacket()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Transaction.objects.filter(transaction_type="LOAN", item=self.central_item).exists())
        self.assertEqual(Stock.objects.get(item=self.central_item, location=self.central_location).quantity, 3)

    def test_department_manager_can_create_own_item_but_not_central_item(self):
        role = self.scoped_manager.department_roles.get(department=self.department)
        role.groups.first().permissions.add(
            Permission.objects.get(content_type__app_label="inventory", codename="add_item")
        )
        self.client.force_authenticate(user=self.scoped_manager)

        own = self.client.post(
            "/api/v1/inventory/items/",
            {"name": "Department tent", "category": self.central_item.category_id, "department": self.department.pk},
            format="json",
        )
        central = self.client.post(
            "/api/v1/inventory/items/",
            {"name": "Central tent", "category": self.central_item.category_id, "department": None},
            format="json",
        )

        self.assertEqual(own.status_code, status.HTTP_201_CREATED, own.data)
        self.assertEqual(central.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Item.objects.get(name="Department tent").department_id, self.department.pk)
        self.assertFalse(Item.objects.filter(name="Central tent").exists())
