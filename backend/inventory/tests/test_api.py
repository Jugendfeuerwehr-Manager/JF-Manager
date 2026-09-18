from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient, APITestCase

from departments.models import Department
from inventory.models import Category, Item, Stock, StorageLocation, Transaction
from members.models import Member


class InventoryAPITest(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pw12345")
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=["view_item", "add_transaction"]))
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name="Helm")
        self.item = Item.objects.create(name="Helm A", category=self.category)
        self.location = StorageLocation.objects.create(name="Lager 1")
        Stock.objects.create(item=self.item, location=self.location, quantity=5)
        self.department = Department.objects.create(name="Abteilung Test", code="dept-test")

    def test_list_items(self):
        url = "/api/v1/inventory/items/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_item_stock_action(self):
        url = f"/api/v1/inventory/items/{self.item.id}/stock/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 5)

    def test_item_standard_item_flag_is_exposed(self):
        self.item.is_standard_item = True
        self.item.save(update_fields=["is_standard_item"])

        response = self.client.get(f"/api/v1/inventory/items/{self.item.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_standard_item"])

    def test_items_can_be_filtered_to_standard_items(self):
        Item.objects.create(name="Nicht Standard", category=self.category)
        self.item.is_standard_item = True
        self.item.save(update_fields=["is_standard_item"])

        response = self.client.get("/api/v1/inventory/items/?is_standard_item=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([entry["name"] for entry in response.data["results"]], [self.item.name])

    def test_batch_loan_issues_multiple_items(self):
        second_item = Item.objects.create(name="Handschuhe", category=self.category)
        Stock.objects.create(item=second_item, location=self.location, quantity=3)
        member = Member.objects.create(name="Max", lastname="Mustermann")

        response = self.client.post(
            "/api/v1/inventory/transactions/batch-loan/",
            {
                "member": member.id,
                "items": [
                    {"item": self.item.id, "quantity": 2},
                    {"item": second_item.id, "quantity": 1},
                ],
                "note": "Ersteinkleidung",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["transactions"]), 2)
        self.assertEqual(Transaction.objects.filter(transaction_type="LOAN").count(), 2)
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 3)
        self.assertEqual(Stock.objects.get(item=second_item, location=self.location).quantity, 2)

    def test_batch_loan_can_create_order_for_missing_mapped_item(self):
        # No manual OrderableItem creation needed: the order/inventory sync signal
        # already provisioned one automatically when self.item was created.
        member = Member.objects.create(name="Erika", lastname="Musterfrau")
        member.departments.add(self.department)

        response = self.client.post(
            "/api/v1/inventory/transactions/batch-loan/",
            {
                "member": member.id,
                "items": [{"item": self.item.id, "quantity": 6}],
                "order_missing": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["missing_count"], 1)
        self.assertEqual(response.data["order"]["member"], member.id)
        self.assertEqual(response.data["order"]["department"], self.department.id)
        self.assertEqual(response.data["order"]["items"][0]["quantity"], 1)
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 0)

    def test_batch_loan_rejects_insufficient_stock_without_changes(self):
        member = Member.objects.create(name="Erika", lastname="Musterfrau")

        response = self.client.post(
            "/api/v1/inventory/transactions/batch-loan/",
            {"member": member.id, "items": [{"item": self.item.id, "quantity": 6}]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(StorageLocation.objects.filter(member=member, is_member=True).exists())
        self.assertFalse(Transaction.objects.filter(transaction_type="LOAN").exists())
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 5)
