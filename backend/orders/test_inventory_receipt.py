from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from inventory.models import Category, Item, ItemVariant, Stock, StorageLocation, Transaction
from members.models import Member
from orders.models import Order, OrderableItem, OrderItem, OrderStatus


class OrderReceiptTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="receiver", password="pw12345", is_staff=True)
        self.user.user_permissions.add(Permission.objects.get(codename="can_change_order_status"))
        self.client.force_authenticate(self.user)
        self.ordered = OrderStatus.objects.get(code="ORDERED")
        self.received = OrderStatus.objects.get(code="RECEIVED")
        self.member = Member.objects.create(name="Max", lastname="Muster")
        self.order = Order.objects.create(member=self.member, ordered_by=self.user)
        self.category = Category.objects.create(name="Bekleidung")
        self.inventory_item = Item.objects.create(name="Jacke", category=self.category, is_variant_parent=True)
        self.variant = ItemVariant.objects.create(parent_item=self.inventory_item, variant_attributes={"size": "M"})
        self.orderable = OrderableItem.objects.get(inventory_item=self.inventory_item)
        self.line = OrderItem.objects.create(
            order=self.order, item=self.orderable, size="M", quantity=2, status=self.ordered
        )
        self.location = StorageLocation.objects.create(name="Hauptlager")

    def test_receiving_books_exact_variant_once(self):
        url = f"/api/v1/order-items/{self.line.pk}/update_status/"
        response = self.client.post(url, {"status": self.received.pk, "receipt_location": self.location.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.line.refresh_from_db()
        self.assertIsNotNone(self.line.receipt_transaction_id)
        self.assertIsNotNone(self.line.received_date)
        receipt = self.line.receipt_transaction
        self.assertEqual(
            (receipt.transaction_type, receipt.item_variant_id, receipt.quantity, receipt.target_id),
            ("IN", self.variant.pk, 2, self.location.pk),
        )
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=self.location).quantity, 2)
        retry = self.client.post(url, {"status": self.received.pk, "receipt_location": self.location.pk})
        self.assertEqual(retry.status_code, 200, retry.data)
        self.assertEqual(Transaction.objects.filter(transaction_type="IN").count(), 1)

    def test_receipt_requires_location_and_unambiguous_variant(self):
        url = f"/api/v1/order-items/{self.line.pk}/update_status/"
        response = self.client.post(url, {"status": self.received.pk})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transaction.objects.exists())
        self.line.size = "XL"
        self.line.save()
        response = self.client.post(url, {"status": self.received.pk, "receipt_location": self.location.pk})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transaction.objects.exists())
        self.line.refresh_from_db()
        self.assertEqual(self.line.status_id, self.ordered.pk)

    def test_bulk_receipt_is_atomic(self):
        second = OrderItem.objects.create(
            order=self.order, item=self.orderable, size="bad", quantity=1, status=self.ordered
        )
        response = self.client.post(
            "/api/v1/order-items/bulk_update_status/",
            {"item_ids": [self.line.pk, second.pk], "status": self.received.pk, "receipt_location": self.location.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Transaction.objects.exists())
        self.line.refresh_from_db()
        self.assertEqual(self.line.status_id, self.ordered.pk)

    def test_unmapped_legacy_item_can_change_status_without_stock(self):
        legacy = OrderableItem.objects.create(name="Altartikel", category="Sonstiges", has_sizes=False)
        line = OrderItem.objects.create(order=self.order, item=legacy, status=self.ordered)
        response = self.client.post(f"/api/v1/order-items/{line.pk}/update_status/", {"status": self.received.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(Transaction.objects.exists())

    def test_patch_status_uses_same_receipt_path(self):
        response = self.client.patch(
            f"/api/v1/order-items/{self.line.pk}/",
            {"status": self.received.pk, "receipt_location": self.location.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=self.location).quantity, 2)

    def test_bulk_receipt_books_each_position(self):
        second = OrderItem.objects.create(
            order=self.order, item=self.orderable, size="M", quantity=1, status=self.ordered
        )
        response = self.client.post(
            "/api/v1/order-items/bulk_update_status/",
            {"item_ids": [self.line.pk, second.pk], "status": self.received.pk, "receipt_location": self.location.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=self.location).quantity, 3)
        self.assertEqual(Transaction.objects.filter(transaction_type="IN").count(), 2)

    def test_delivery_can_create_member_loan_once(self):
        self.client.post(
            f"/api/v1/order-items/{self.line.pk}/update_status/",
            {"status": self.received.pk, "receipt_location": self.location.pk},
        )
        delivered = OrderStatus.objects.get(code="DELIVERED")
        url = f"/api/v1/order-items/{self.line.pk}/update_status/"

        response = self.client.post(url, {"status": delivered.pk, "create_loan": True}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.line.refresh_from_db()
        loan = self.line.loan_transaction
        self.assertEqual((loan.transaction_type, loan.source_id, loan.quantity), ("LOAN", self.location.pk, 2))
        self.assertEqual(loan.target.member_id, self.member.pk)
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=self.location).quantity, 0)
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=loan.target).quantity, 2)

        retry = self.client.post(url, {"status": delivered.pk, "create_loan": True}, format="json")
        self.assertEqual(retry.status_code, 200, retry.data)
        self.assertEqual(Transaction.objects.filter(transaction_type="LOAN").count(), 1)

    def test_delivery_without_confirmation_does_not_create_loan(self):
        self.client.post(
            f"/api/v1/order-items/{self.line.pk}/update_status/",
            {"status": self.received.pk, "receipt_location": self.location.pk},
        )
        delivered = OrderStatus.objects.get(code="DELIVERED")
        response = self.client.post(
            f"/api/v1/order-items/{self.line.pk}/update_status/",
            {"status": delivered.pk, "create_loan": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.line.refresh_from_db()
        self.assertIsNone(self.line.loan_transaction_id)
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=self.location).quantity, 2)

    def test_delivery_requires_receipt_for_automatic_loan(self):
        self.line.status = self.received
        self.line.save()
        delivered = OrderStatus.objects.get(code="DELIVERED")
        response = self.client.post(
            f"/api/v1/order-items/{self.line.pk}/update_status/",
            {"status": delivered.pk, "create_loan": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.line.refresh_from_db()
        self.assertEqual(self.line.status_id, self.received.pk)

    def test_bulk_delivery_rolls_back_if_stock_is_insufficient(self):
        second = OrderItem.objects.create(
            order=self.order, item=self.orderable, size="M", quantity=2, status=self.ordered
        )
        for line in (self.line, second):
            response = self.client.post(
                f"/api/v1/order-items/{line.pk}/update_status/",
                {"status": self.received.pk, "receipt_location": self.location.pk},
            )
            self.assertEqual(response.status_code, 200, response.data)
        Transaction.objects.create(transaction_type="OUT", item_variant=self.variant, source=self.location, quantity=1)
        delivered = OrderStatus.objects.get(code="DELIVERED")

        response = self.client.post(
            "/api/v1/order-items/bulk_update_status/",
            {"item_ids": [self.line.pk, second.pk], "status": delivered.pk, "create_loan": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Transaction.objects.filter(transaction_type="LOAN").exists())
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=self.location).quantity, 3)
        self.line.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.line.status_id, self.received.pk)
        self.assertEqual(second.status_id, self.received.pk)

    def test_bulk_delivery_creates_loans_for_both_positions(self):
        second = OrderItem.objects.create(
            order=self.order, item=self.orderable, size="M", quantity=1, status=self.ordered
        )
        for line in (self.line, second):
            response = self.client.post(
                f"/api/v1/order-items/{line.pk}/update_status/",
                {"status": self.received.pk, "receipt_location": self.location.pk},
            )
            self.assertEqual(response.status_code, 200, response.data)
        delivered = OrderStatus.objects.get(code="DELIVERED")

        response = self.client.post(
            "/api/v1/order-items/bulk_update_status/",
            {"item_ids": [self.line.pk, second.pk], "status": delivered.pk, "create_loan": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Transaction.objects.filter(transaction_type="LOAN").count(), 2)
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=self.location).quantity, 0)
        member_location = StorageLocation.objects.get(member=self.member)
        self.assertEqual(Stock.objects.get(item_variant=self.variant, location=member_location).quantity, 3)
