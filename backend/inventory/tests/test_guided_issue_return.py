"""UX-05.1: availability, code lookup, guided return and article history."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from inventory.models import Category, Item, ItemVariant, Stock, StockBookingRequest, StorageLocation, Transaction
from inventory.opening_stock import book_opening_stock
from members.models import Member
from orders.models import Order, OrderableItem, OrderItem, OrderStatus

INVENTORY_RIGHTS = ["view_item", "view_stock", "view_transaction", "view_storagelocation", "add_transaction"]


class GuidedInventoryTestBase(APITestCase):
    def setUp(self):
        self.dept_a = Department.objects.create(name="Abteilung A", code="ux05-a")
        self.dept_b = Department.objects.create(name="Abteilung B", code="ux05-b")
        self.user = self.department_user("clerk-a", self.dept_a, [*INVENTORY_RIGHTS, "view_order"])
        self.client.force_authenticate(self.user)

        category = Category.objects.create(name="Bekleidung")
        self.store_a = StorageLocation.objects.create(name="Lager A", department=self.dept_a)
        self.store_b = StorageLocation.objects.create(name="Lager B", department=self.dept_b)
        self.shirt = Item.objects.create(
            name="Shirt", category=category, department=self.dept_a, is_variant_parent=True, identifier2="SHIRT-A"
        )
        self.size_m = ItemVariant.objects.create(parent_item=self.shirt, variant_attributes={"größe": "M"}, sku="SH-M")
        self.size_l = ItemVariant.objects.create(parent_item=self.shirt, variant_attributes={"größe": "L"}, sku="SH-L")
        self.helmet = Item.objects.create(name="Helm", category=category, department=self.dept_a, identifier1="H-1")
        self.foreign = Item.objects.create(name="Fremd", category=category, department=self.dept_b, identifier2="X-B")
        book_opening_stock(self.store_a, 5, item_variant=self.size_m)
        book_opening_stock(self.store_a, 4, item=self.helmet)
        book_opening_stock(self.store_b, 3, item=self.foreign)

        self.member = Member.objects.create(name="Alex", lastname="Synthetisch")
        self.member.departments.add(self.dept_a)
        self.member_location = StorageLocation.objects.create(
            name="Alex Synthetisch", is_member=True, member=self.member, department=self.dept_a
        )
        Transaction.objects.create(
            transaction_type="LOAN",
            item_variant=self.size_m,
            source=self.store_a,
            target=self.member_location,
            quantity=2,
        )
        Transaction.objects.create(
            transaction_type="LOAN", item=self.helmet, source=self.store_a, target=self.member_location, quantity=1
        )

    def department_user(self, username, department, codenames):
        user = get_user_model().objects.create_user(username=username, password="pw12345")
        group = Group.objects.create(name=f"{username}-role")
        group.permissions.set(Permission.objects.filter(codename__in=codenames))
        role = UserDepartmentRole.objects.create(user=user, department=department)
        role.groups.add(group)
        return user

    def order_line(self, item, size, quantity, code, department=None):
        order = Order.objects.create(member=self.member, department=department or self.dept_a)
        return OrderItem.objects.create(
            order=order,
            item=OrderableItem.objects.get(inventory_item=item),
            size=size,
            quantity=quantity,
            status=OrderStatus.objects.get(code=code),
        )


class AvailabilityTests(GuidedInventoryTestBase):
    def rows(self, response):
        return {(row["item"], row["item_variant"]): row for row in response.data["results"]}

    def test_separates_available_issued_and_open_orders(self):
        self.order_line(self.shirt, "M", 2, "ORDERED")
        self.order_line(self.shirt, "L", 1, "NEW")
        self.order_line(self.shirt, "M", 5, "CANCELLED")
        self.order_line(self.helmet, "", 3, "DELIVERED")
        self.order_line(self.shirt, "XXL", 1, "ORDERED")

        response = self.client.get("/api/v1/inventory/items/availability/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["can_view_orders"])
        rows = self.rows(response)
        self.assertEqual(
            {key: (row["available"], row["issued"], row["ordered"]) for key, row in rows.items()},
            {
                (self.shirt.pk, self.size_m.pk): (3, 2, 2),
                (self.shirt.pk, self.size_l.pk): (0, 0, 1),
                # Size without a matching variant stays visible on the article.
                (self.shirt.pk, None): (0, 0, 1),
                (self.helmet.pk, None): (3, 1, 0),
            },
        )

    def test_received_lines_no_longer_count_as_ordered(self):
        line = self.order_line(self.helmet, "", 2, "ORDERED")
        receipt = Transaction.objects.create(transaction_type="IN", item=self.helmet, target=self.store_a, quantity=2)
        OrderItem.objects.filter(pk=line.pk).update(receipt_transaction=receipt)

        rows = self.rows(self.client.get(f"/api/v1/inventory/items/availability/?item={self.helmet.pk}"))

        self.assertEqual(list(rows), [(self.helmet.pk, None)])
        self.assertEqual(rows[(self.helmet.pk, None)]["ordered"], 0)
        self.assertEqual(rows[(self.helmet.pk, None)]["available"], 5)

    def test_foreign_department_items_and_orders_stay_hidden(self):
        self.order_line(self.helmet, "", 4, "ORDERED", department=self.dept_b)

        rows = self.rows(self.client.get("/api/v1/inventory/items/availability/"))

        self.assertNotIn((self.foreign.pk, None), rows)
        self.assertEqual(rows[(self.helmet.pk, None)]["ordered"], 0)

    def test_ordered_is_unknown_without_order_read_right(self):
        user = self.department_user("no-orders", self.dept_a, INVENTORY_RIGHTS)
        self.client.force_authenticate(user)

        response = self.client.get("/api/v1/inventory/items/availability/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_view_orders"])
        self.assertTrue(all(row["ordered"] is None for row in response.data["results"]))

    def test_requires_item_read_right_and_login(self):
        self.client.force_authenticate(self.department_user("nothing", self.dept_a, []))
        self.assertEqual(self.client.get("/api/v1/inventory/items/availability/").status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get("/api/v1/inventory/items/availability/").status_code, (401, 403))

    def test_rejects_malformed_item_filter(self):
        self.assertEqual(self.client.get("/api/v1/inventory/items/availability/?item=abc").status_code, 400)


class CodeLookupTests(GuidedInventoryTestBase):
    def lookup(self, code):
        return self.client.get("/api/v1/inventory/items/lookup/", {"code": code})

    def test_finds_size_number_barcode_and_inventory_number_case_insensitive(self):
        size = self.lookup(" sh-m ")
        barcode = self.lookup("shirt-a")
        number = self.lookup("H-1")

        self.assertEqual(size.status_code, 200, size.data)
        self.assertEqual(
            [(row["item"], row["item_variant"]) for row in size.data["results"]], [(self.shirt.pk, self.size_m.pk)]
        )
        self.assertEqual(barcode.data["results"][0]["item_variant"], None)
        self.assertTrue(barcode.data["results"][0]["is_variant_parent"])
        self.assertEqual(number.data["results"][0]["item"], self.helmet.pk)

    def test_unknown_and_foreign_codes_find_nothing(self):
        self.assertEqual(self.lookup("UNBEKANNT").data["results"], [])
        self.assertEqual(self.lookup("X-B").data["results"], [])

    def test_empty_code_is_rejected_and_rights_are_required(self):
        self.assertEqual(self.lookup("  ").status_code, 400)
        self.client.force_authenticate(self.department_user("lookup-none", self.dept_a, []))
        self.assertEqual(self.lookup("H-1").status_code, 403)


class BatchReturnTests(GuidedInventoryTestBase):
    url = "/api/v1/inventory/transactions/batch-return/"

    def payload(self, **overrides):
        data = {
            "member": self.member.pk,
            "items": [
                {"item_variant": self.size_m.pk, "quantity": 1, "target": self.store_a.pk},
                {"item": self.helmet.pk, "quantity": 1, "target": self.store_a.pk},
            ],
            "note": "Rücknahme Test",
        }
        data.update(overrides)
        return data

    def held(self, **identity):
        return Stock.objects.get(location=self.member_location, **identity).quantity

    def test_returns_part_quantities_in_one_booking(self):
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["returned_quantity"], 2)
        self.assertEqual({row["transaction_type"] for row in response.data["transactions"]}, {"RETURN"})
        self.assertEqual((self.held(item_variant=self.size_m), self.held(item=self.helmet)), (1, 0))
        self.assertEqual(Stock.objects.get(location=self.store_a, item_variant=self.size_m).quantity, 4)

    def test_over_return_rejects_every_line(self):
        payload = self.payload(
            items=[
                {"item": self.helmet.pk, "quantity": 1, "target": self.store_a.pk},
                {"item_variant": self.size_m.pk, "quantity": 3, "target": self.store_a.pk},
            ]
        )

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("2 ausgegeben, 3 zur Rücknahme", str(response.data["items"]))
        self.assertEqual(Transaction.objects.filter(transaction_type="RETURN").count(), 0)
        self.assertEqual(self.held(item=self.helmet), 1)

    def test_size_never_issued_is_rejected(self):
        payload = self.payload(items=[{"item_variant": self.size_l.pk, "quantity": 1, "target": self.store_a.pk}])
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("0 ausgegeben", str(response.data["items"]))

    def test_member_location_is_not_a_return_target_and_duplicates_are_rejected(self):
        member_target = self.payload(items=[{"item": self.helmet.pk, "quantity": 1, "target": self.member_location.pk}])
        duplicate = self.payload(
            items=[
                {"item": self.helmet.pk, "quantity": 1, "target": self.store_a.pk},
                {"item": self.helmet.pk, "quantity": 1, "target": self.store_a.pk},
            ]
        )
        self.assertEqual(self.client.post(self.url, member_target, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url, duplicate, format="json").status_code, 400)

    def test_foreign_department_member_and_target_are_rejected(self):
        stranger = Member.objects.create(name="Kim", lastname="Fremd")
        stranger.departments.add(self.dept_b)
        foreign_target = self.payload(items=[{"item": self.helmet.pk, "quantity": 1, "target": self.store_b.pk}])

        self.assertEqual(self.client.post(self.url, self.payload(member=stranger.pk), format="json").status_code, 403)
        self.assertEqual(self.client.post(self.url, foreign_target, format="json").status_code, 400)
        self.assertEqual(Transaction.objects.filter(transaction_type="RETURN").count(), 0)

    def test_booking_right_and_login_are_required(self):
        self.client.force_authenticate(self.department_user("reader", self.dept_a, ["view_transaction"]))
        self.assertEqual(self.client.post(self.url, self.payload(), format="json").status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.client.post(self.url, self.payload(), format="json").status_code, (401, 403))
        self.assertEqual(Transaction.objects.filter(transaction_type="RETURN").count(), 0)

    def test_member_without_issued_items_gets_clear_error(self):
        other = Member.objects.create(name="Noa", lastname="Leer")
        other.departments.add(self.dept_a)
        response = self.client.post(self.url, self.payload(member=other.pk), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("nichts ausgegeben", str(response.data))

    def test_idempotency_key_replays_once_and_rejects_changed_content(self):
        headers = {"HTTP_IDEMPOTENCY_KEY": "ux05-return-1"}
        first = self.client.post(self.url, self.payload(), format="json", **headers)
        replay = self.client.post(self.url, self.payload(), format="json", **headers)
        changed = self.client.post(self.url, self.payload(note="anders"), format="json", **headers)

        self.assertEqual((first.status_code, replay.status_code, changed.status_code), (201, 201, 409))
        self.assertEqual(replay.data, first.data)
        self.assertEqual(Transaction.objects.filter(transaction_type="RETURN").count(), 2)
        self.assertEqual(StockBookingRequest.objects.count(), 1)


class HistoryAndIssueMessageTests(GuidedInventoryTestBase):
    def test_article_history_covers_all_sizes(self):
        response = self.client.get(f"/api/v1/inventory/transactions/?item_variant__parent_item={self.shirt.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            sorted(row["transaction_type"] for row in response.data["results"]), ["IN", "LOAN"], response.data
        )

    def test_shortage_message_names_article_and_remaining_quantity(self):
        response = self.client.post(
            "/api/v1/inventory/transactions/batch-loan/",
            {"member": self.member.pk, "items": [{"item": self.helmet.pk, "quantity": 9}]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Helm: nur 3 verfügbar, 9 angefordert", str(response.data["items"]))
