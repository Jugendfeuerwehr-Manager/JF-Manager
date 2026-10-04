"""Mixed department targets in batch writes must leave no partial changes."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from inventory.models import Category, Item, Stock, StorageLocation, Transaction
from members.models import Member


class InventoryBatchTargetAtomicityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="batch-target-a")
        cls.department_b = Department.objects.create(name="B", code="batch-target-b")
        cls.member_a = Member.objects.create(name="A", lastname="Member")
        cls.member_a.departments.add(cls.department_a)
        category = Category.objects.create(name="Equipment")
        cls.item_a = Item.objects.create(name="A item", category=category, department=cls.department_a)
        cls.item_b = Item.objects.create(name="B item", category=category, department=cls.department_b)
        cls.location_a = StorageLocation.objects.create(name="A shelf", department=cls.department_a)
        cls.location_b = StorageLocation.objects.create(name="B shelf", department=cls.department_b)
        Stock.objects.create(item=cls.item_a, location=cls.location_a, quantity=2)
        Stock.objects.create(item=cls.item_b, location=cls.location_b, quantity=2)

        cls.user = get_user_model().objects.create_user(username="batch-target-writer")
        writer = AuthGroup.objects.create(name="Batch target writer A")
        writer.permissions.add(
            Permission.objects.get(content_type__app_label="inventory", codename="add_transaction")
        )
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_a).groups.add(writer)
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_b)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_mixed_batch_loan_rejects_every_line_without_side_effects(self):
        response = self.client.post(
            "/api/v1/inventory/transactions/batch-loan/",
            {
                "member": self.member_a.pk,
                "items": [
                    {"item": self.item_a.pk, "quantity": 1},
                    {"item": self.item_b.pk, "quantity": 1},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(Stock.objects.get(item=self.item_a, location=self.location_a).quantity, 2)
        self.assertEqual(Stock.objects.get(item=self.item_b, location=self.location_b).quantity, 2)
        self.assertFalse(StorageLocation.objects.filter(member=self.member_a).exists())
