"""SEC-09.1: failing contracts for immutable and repeat-safe stock movements."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.models import Item, Stock, StorageLocation, Transaction


class StockLedgerRegressionTest(TestCase):
    def setUp(self):
        self.item = Item.objects.create(name="Testartikel")
        self.location = StorageLocation.objects.create(name="Testlager")
        self.user = get_user_model().objects.create_user(username="stock-ledger", password="unused")
        self.user.user_permissions.add(
            Permission.objects.get(codename="can_access_all_departments"),
            *Permission.objects.filter(
                content_type__app_label="inventory",
                codename__in=["add_transaction", "change_transaction", "delete_transaction", "view_transaction"],
            ),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _receipt(self):
        return Transaction.objects.create(
            transaction_type="IN", item=self.item, target=self.location, quantity=2, user=self.user
        )

    def test_saving_booked_transaction_again_does_not_post_stock_twice(self):
        movement = self._receipt()

        movement.save()

        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 2)

    def test_changing_booked_transaction_is_rejected_without_stock_effect(self):
        movement = self._receipt()
        movement.quantity = 5

        with self.assertRaises(ValidationError):
            movement.save(update_fields=["quantity"])

        movement.refresh_from_db()
        self.assertEqual(movement.quantity, 2)
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 2)

    def test_api_does_not_allow_deleting_booked_transaction(self):
        movement = self._receipt()

        response = self.client.delete(f"/api/v1/inventory/transactions/{movement.pk}/")

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Transaction.objects.filter(pk=movement.pk).exists())
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 2)

    def test_same_idempotency_key_replays_one_receipt(self):
        payload = {"transaction_type": "IN", "item": self.item.pk, "target": self.location.pk, "quantity": 2}
        headers = {"HTTP_IDEMPOTENCY_KEY": "sec09-receipt-1"}

        first = self.client.post("/api/v1/inventory/transactions/", payload, format="json", **headers)
        second = self.client.post("/api/v1/inventory/transactions/", payload, format="json", **headers)

        self.assertEqual(first.status_code, 201, first.data)
        self.assertIn(second.status_code, (200, 201), second.data)
        self.assertEqual(second.data["id"], first.data["id"])
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 2)

    def test_reused_idempotency_key_with_different_payload_is_rejected(self):
        payload = {"transaction_type": "IN", "item": self.item.pk, "target": self.location.pk, "quantity": 2}
        headers = {"HTTP_IDEMPOTENCY_KEY": "sec09-receipt-2"}
        first = self.client.post("/api/v1/inventory/transactions/", payload, format="json", **headers)
        changed = self.client.post(
            "/api/v1/inventory/transactions/", {**payload, "quantity": 3}, format="json", **headers
        )

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(changed.status_code, 409, changed.data)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 2)

    def test_stock_identity_cannot_be_duplicated(self):
        Stock.objects.create(item=self.item, location=self.location, quantity=2)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Stock.objects.create(item=self.item, location=self.location, quantity=3)

        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 2)
