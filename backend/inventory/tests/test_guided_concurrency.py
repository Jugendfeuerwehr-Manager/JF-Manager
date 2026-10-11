"""UX-05.1: two sessions compete for the same remaining quantity (PostgreSQL only)."""

from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from inventory.models import Item, ItemVariant, Stock, StorageLocation, Transaction
from inventory.opening_stock import book_opening_stock
from members.models import Member

from .test_postgres_concurrency import run_parallel

RIGHTS = ["can_access_all_departments", "add_transaction", "view_transaction", "view_stock"]


@skipUnless(connection.vendor == "postgresql", "concurrency contract needs PostgreSQL")
class GuidedBookingConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.shirt = Item.objects.create(name="Session shirt", is_variant_parent=True)
        self.size = ItemVariant.objects.create(parent_item=self.shirt, variant_attributes={"größe": "M"})
        self.store = StorageLocation.objects.create(name="Session store")
        self.clients = []
        for index in range(2):
            user = get_user_model().objects.create_user(username=f"session-clerk-{index}", password="pw12345")
            user.user_permissions.add(*Permission.objects.filter(codename__in=RIGHTS))
            client = APIClient()
            client.force_login(user)  # one real session cookie per clerk
            self.clients.append(client)

    def held(self, location):
        return Stock.objects.get(location=location, item_variant=self.size).quantity

    def test_two_sessions_cannot_issue_the_same_remaining_quantity(self):
        book_opening_stock(self.store, 3, item_variant=self.size)
        members = [Member.objects.create(name=f"Session {index}", lastname="Synthetisch") for index in range(2)]

        def issue(index):
            response = self.clients[index].post(
                "/api/v1/inventory/transactions/batch-loan/",
                {"member": members[index].pk, "items": [{"item_variant": self.size.pk, "quantity": 2}]},
                format="json",
                HTTP_IDEMPOTENCY_KEY=f"session-issue-{index}",
            )
            return response.status_code, response.data

        results = run_parallel(issue, count=2)

        self.assertEqual(sorted(status for status, _data in results), [201, 400], results)
        rejected = next(data for status, data in results if status == 400)
        self.assertIn("nur 1 verfügbar, 2 angefordert", str(rejected["items"]))
        self.assertEqual(self.held(self.store), 1)
        self.assertEqual(Transaction.objects.filter(transaction_type="LOAN").count(), 1)

    def test_two_sessions_cannot_take_back_the_same_issued_quantity(self):
        book_opening_stock(self.store, 2, item_variant=self.size)
        member = Member.objects.create(name="Session", lastname="Rückgabe")
        member_location = StorageLocation.objects.create(name="Session Rückgabe", is_member=True, member=member)
        Transaction.objects.create(
            transaction_type="LOAN", item_variant=self.size, source=self.store, target=member_location, quantity=2
        )

        def take_back(index):
            response = self.clients[index].post(
                "/api/v1/inventory/transactions/batch-return/",
                {
                    "member": member.pk,
                    "items": [{"item_variant": self.size.pk, "quantity": 2, "target": self.store.pk}],
                },
                format="json",
                HTTP_IDEMPOTENCY_KEY=f"session-return-{index}",
            )
            return response.status_code

        results = run_parallel(take_back, count=2)

        self.assertEqual(sorted(results), [201, 400], results)
        self.assertEqual((self.held(member_location), self.held(self.store)), (0, 2))
        self.assertEqual(Transaction.objects.filter(transaction_type="RETURN").count(), 1)
