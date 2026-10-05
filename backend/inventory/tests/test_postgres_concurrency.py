"""SEC-09.6: concurrency, rollback and replay on PostgreSQL.

SQLite serialises writers and cannot show lost updates or deadlocks, so these
tests only run against PostgreSQL (see docs/operations/inventory-ledger.md).
"""

import threading
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from inventory.models import Item, Stock, StockBookingRequest, StorageLocation, Transaction
from inventory.opening_stock import book_opening_stock
from members.models import Member

WORKERS = 8


def run_parallel(task, count=WORKERS):
    """Start ``count`` threads at the same moment; return results or exceptions."""
    barrier = threading.Barrier(count)
    results = [None] * count

    def worker(index):
        try:
            barrier.wait()
            results[index] = task(index)
        except Exception as exc:
            results[index] = exc
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return results


@skipUnless(connection.vendor == "postgresql", "concurrency contract needs PostgreSQL")
class LedgerConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.item = Item.objects.create(name="Concurrent helmet")
        self.store = StorageLocation.objects.create(name="Concurrent store")
        self.user = get_user_model().objects.create_user(username="concurrent-clerk")
        self.user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["can_access_all_departments", "add_transaction", "view_transaction", "view_stock"]
            )
        )

    def stock(self, location):
        return Stock.objects.get(item=self.item, location=location).quantity

    def test_parallel_issues_never_oversell_or_lose_updates(self):
        book_opening_stock(self.store, 5, item=self.item)
        target = StorageLocation.objects.create(name="Concurrent target")

        def issue(_index):
            return Transaction.objects.create(
                transaction_type="MOVE", item=self.item, source=self.store, target=target, quantity=1
            )

        results = run_parallel(issue)
        booked = [result for result in results if isinstance(result, Transaction)]
        rejected = [result for result in results if isinstance(result, ValidationError)]
        self.assertEqual((len(booked), len(rejected)), (5, WORKERS - 5), results)
        self.assertEqual((self.stock(self.store), self.stock(target)), (0, 5))

    def test_opposite_transfers_do_not_deadlock_and_conserve_totals(self):
        other = StorageLocation.objects.create(name="Concurrent other")
        book_opening_stock(self.store, 20, item=self.item)
        book_opening_stock(other, 20, item=self.item)

        def transfer(index):
            source, target = (self.store, other) if index % 2 else (other, self.store)
            return Transaction.objects.create(
                transaction_type="MOVE", item=self.item, source=source, target=target, quantity=1
            )

        results = run_parallel(transfer)
        self.assertTrue(all(isinstance(result, Transaction) for result in results), results)
        self.assertEqual(self.stock(self.store) + self.stock(other), 40)

    def test_same_idempotency_key_books_once_under_parallel_retries(self):
        book_opening_stock(self.store, 10, item=self.item)
        target = StorageLocation.objects.create(name="Replay target")
        payload = {
            "transaction_type": "MOVE",
            "item": self.item.pk,
            "source": self.store.pk,
            "target": target.pk,
            "quantity": 3,
        }

        def submit(_index):
            client = APIClient()
            client.force_authenticate(self.user)
            response = client.post(
                "/api/v1/inventory/transactions/", payload, format="json", HTTP_IDEMPOTENCY_KEY="parallel-retry"
            )
            return response.status_code, response.data.get("id")

        results = run_parallel(submit)
        self.assertTrue(all(isinstance(result, tuple) for result in results), results)
        self.assertEqual({status for status, _id in results} - {200, 201}, set(), results)
        self.assertEqual(len({movement_id for _status, movement_id in results}), 1)
        self.assertEqual(Transaction.objects.filter(transaction_type="MOVE").count(), 1)
        self.assertEqual((self.stock(self.store), self.stock(target)), (7, 3))
        self.assertEqual(StockBookingRequest.objects.count(), 1)

    def test_parallel_batch_loans_with_crossed_line_order_stay_atomic(self):
        second = Item.objects.create(name="Concurrent jacket")
        book_opening_stock(self.store, 3, item=self.item)
        book_opening_stock(self.store, 3, item=second)
        members = [Member.objects.create(name=f"Synthetic {index}", lastname="Borrower") for index in range(WORKERS)]

        def borrow(index):
            lines = [{"item": self.item.pk, "quantity": 1}, {"item": second.pk, "quantity": 1}]
            client = APIClient()
            client.force_authenticate(self.user)
            response = client.post(
                "/api/v1/inventory/transactions/batch-loan/",
                {"member": members[index].pk, "items": lines if index % 2 else list(reversed(lines))},
                format="json",
            )
            return response.status_code

        results = run_parallel(borrow)
        self.assertEqual(sorted(results), [201] * 3 + [400] * (WORKERS - 3), results)
        self.assertEqual(Stock.objects.get(item=self.item, location=self.store).quantity, 0)
        self.assertEqual(Stock.objects.get(item=second, location=self.store).quantity, 0)
        # Every successful loan booked both lines; failed ones booked nothing.
        loans = Transaction.objects.filter(transaction_type="LOAN")
        self.assertEqual(loans.count(), 6)
        self.assertEqual(set(loans.values_list("target__member", flat=True).distinct().order_by()).__len__(), 3)
