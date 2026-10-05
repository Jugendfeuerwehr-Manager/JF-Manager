"""SEC-09.5b: no path besides bookings may change stock or booked movements."""

from io import StringIO
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import DatabaseError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.models import Item, Stock, StorageLocation, Transaction
from inventory.opening_stock import book_opening_stock


class LedgerGuardTests(TestCase):
    def setUp(self):
        self.item = Item.objects.create(name="Synthetic helmet")
        self.location = StorageLocation.objects.create(name="Synthetic store")
        self.stock = book_opening_stock(self.location, 5, item=self.item)
        self.movement = Transaction.objects.get()

    def assert_unchanged(self):
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_opening_balance_is_an_incoming_booking(self):
        self.assertEqual(self.movement.transaction_type, "IN")
        self.assertEqual(self.movement.quantity, 5)

    def test_bulk_changes_to_movements_are_rejected(self):
        with self.assertRaises(ValidationError):
            Transaction.objects.filter(pk=self.movement.pk).update(quantity=50)
        with self.assertRaises(ValidationError):
            Transaction.objects.all().delete()
        self.assert_unchanged()

    def test_bulk_and_direct_stock_changes_are_rejected(self):
        with self.assertRaises(ValidationError):
            Stock.objects.filter(pk=self.stock.pk).update(quantity=50)
        self.stock.quantity = 50
        with self.assertRaises(ValidationError):
            self.stock.save()
        with self.assertRaises(ValidationError):
            Stock.objects.create(item=Item.objects.create(name="Other"), location=self.location, quantity=3)
        self.assert_unchanged()

    def test_stock_with_quantity_cannot_be_deleted(self):
        with self.assertRaises(ValidationError):
            Stock.objects.filter(pk=self.stock.pk).delete()
        with self.assertRaises(ValidationError):
            Stock.objects.get(pk=self.stock.pk).delete()
        empty = Stock.objects.create(item=Item.objects.create(name="Empty"), location=self.location)
        empty.delete()
        self.assert_unchanged()

    def test_cascades_cannot_remove_booked_movements_or_stock(self):
        with self.assertRaises((ProtectedError, ValidationError)):
            self.location.delete()
        with self.assertRaises((ProtectedError, ValidationError)):
            self.item.delete()
        self.assert_unchanged()

    def test_clearing_former_member_names_is_the_only_bulk_change(self):
        named = Transaction.objects.create(
            transaction_type="IN",
            item=self.item,
            target=self.location,
            quantity=1,
            former_member_name="Former Synthetic",
        )
        user = get_user_model().objects.create_user(username="privacy-admin")
        user.user_permissions.add(Permission.objects.get(codename="clear_former_member_names"))
        client = APIClient()
        client.force_authenticate(user)
        response = client.post("/api/v1/inventory/transactions/clear-former-member-names/")
        self.assertEqual(response.status_code, 200, response.data)
        named.refresh_from_db()
        self.assertEqual(named.former_member_name, "")
        self.assertEqual((named.quantity, Stock.objects.get(pk=self.stock.pk).quantity), (1, 6))

    def test_sample_data_reset_refuses_to_delete_bookings(self):
        with self.assertRaises(CommandError):
            call_command("create_inventory_sample_data", "--clear", stdout=StringIO())
        self.assert_unchanged()


@skipUnless(connection.vendor == "postgresql", "database trigger exists on PostgreSQL only")
class LedgerTriggerTests(TestCase):
    """Raw SQL must not bypass the ledger; run in SEC-09.6 against PostgreSQL."""

    def execute(self, statement):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(statement)

    def test_raw_sql_cannot_change_or_delete_movements(self):
        item = Item.objects.create(name="Trigger item")
        location = StorageLocation.objects.create(name="Trigger store")
        book_opening_stock(location, 2, item=item, note="Synthetic opening")
        for statement in (
            "UPDATE inventory_transaction SET quantity = 9",
            "UPDATE inventory_transaction SET former_member_name = 'Someone'",
            "DELETE FROM inventory_transaction",
        ):
            with self.assertRaises(DatabaseError):
                self.execute(statement)
        self.assertEqual(list(Transaction.objects.values_list("quantity", flat=True)), [2])

    def test_privacy_clearing_is_allowed(self):
        item = Item.objects.create(name="Privacy item")
        location = StorageLocation.objects.create(name="Privacy store")
        Transaction.objects.create(
            transaction_type="IN", item=item, target=location, quantity=1, former_member_name="Former Synthetic"
        )
        self.assertEqual(Transaction.objects.clear_former_member_names(), 1)
        self.assertEqual(Transaction.objects.get().former_member_name, "")
