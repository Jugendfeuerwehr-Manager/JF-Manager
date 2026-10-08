from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.models import Department, RoleTemplate, UserDepartmentRole
from inventory.models import Category, Item, Stock, StorageLocation, Transaction
from inventory.opening_stock import book_opening_stock
from members.models import Member
from orders.models import Order, OrderableItem, OrderItem, OrderStatus


class OperationalRoleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.a = Department.objects.create(name="Operational A", code="operational-a")
        cls.b = Department.objects.create(name="Operational B", code="operational-b")
        cls.member_a = Member.objects.create(
            name="Synthetic A", lastname="Person", email="private-test@example.invalid"
        )
        cls.member_b = Member.objects.create(name="Synthetic B", lastname="Person")
        cls.member_a.departments.add(cls.a)
        cls.member_b.departments.add(cls.b)
        cls.category = Category.objects.create(name="Operational")
        cls.item = Item.objects.create(name="Synthetic supply", category=cls.category, department=cls.a)
        cls.foreign_item = Item.objects.create(name="Foreign supply", category=cls.category, department=cls.b)
        cls.location = StorageLocation.objects.create(name="Operational A", department=cls.a)
        cls.foreign_location = StorageLocation.objects.create(name="Operational B", department=cls.b)
        cls.catalog_item, _ = OrderableItem.objects.update_or_create(
            inventory_item=cls.item,
            defaults={"name": "Synthetic supply", "category": "Operational", "has_sizes": False},
        )
        cls.ordered = OrderStatus.objects.get(code="ORDERED")
        cls.received = OrderStatus.objects.get(code="RECEIVED")
        cls.user = get_user_model().objects.create_user(username="operational-role")
        cls.order = Order.objects.create(member=cls.member_a, department=cls.a)
        cls.line = OrderItem.objects.create(order=cls.order, item=cls.catalog_item, quantity=2, status=cls.ordered)

    def use_role(self, key, organization=False):
        template = RoleTemplate.objects.get(key=key)
        if organization:
            self.user.groups.add(template.group)
        else:
            role, _ = UserDepartmentRole.objects.get_or_create(user=self.user, department=self.a)
            role.groups.set([template.group])
        self.client.force_authenticate(self.user)

    def test_inventory_person_lookup_is_minimal_and_scoped(self):
        self.use_role("inventory_manager")
        response = self.client.get("/api/v1/role-member-options/", {"purpose": "inventory"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["results"],
            [{"id": self.member_a.pk, "full_name": self.member_a.get_full_name(), "department_ids": [self.a.pk]}],
        )
        self.assertEqual(self.client.get("/api/v1/members/").status_code, 403)
        self.assertEqual(
            self.client.get(
                "/api/v1/role-member-options/", {"purpose": "inventory", "department": self.b.pk}
            ).status_code,
            403,
        )

    def test_organization_inventory_lookup_can_select_all_departments(self):
        self.use_role("inventory_manager_organization", True)
        response = self.client.get("/api/v1/role-member-options/", {"purpose": "inventory"})
        self.assertEqual({row["id"] for row in response.data["results"]}, {self.member_a.pk, self.member_b.pk})
        self.assertEqual(self.client.get("/api/v1/members/").status_code, 403)

    def test_order_role_receives_in_own_storage_without_general_inventory_booking_right(self):
        self.use_role("order_manager")
        self.assertFalse(self.user.has_perm("inventory.add_transaction"))
        response = self.client.patch(
            f"/api/v1/order-items/{self.line.pk}/",
            {"status": self.received.pk, "receipt_location": self.location.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 2)
        self.assertEqual(
            self.client.post(
                "/api/v1/inventory/transactions/",
                {"transaction_type": "IN", "item": self.item.pk, "target": self.location.pk, "quantity": 10},
                format="json",
            ).status_code,
            403,
        )

    def test_order_role_cannot_receive_into_foreign_storage_or_for_foreign_item(self):
        self.use_role("order_manager")
        response = self.client.patch(
            f"/api/v1/order-items/{self.line.pk}/",
            {"status": self.received.pk, "receipt_location": self.foreign_location.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transaction.objects.exists())
        foreign, _ = OrderableItem.objects.update_or_create(
            inventory_item=self.foreign_item,
            defaults={"name": "Foreign", "category": "Operational", "has_sizes": False},
        )
        self.line.item = foreign
        self.line.save()
        response = self.client.patch(
            f"/api/v1/order-items/{self.line.pk}/",
            {"status": self.received.pk, "receipt_location": self.foreign_location.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transaction.objects.exists())

    def test_order_role_has_minimal_person_selection_and_creation_defaults_status(self):
        self.use_role("order_manager")
        response = self.client.get("/api/v1/role-member-options/", {"purpose": "orders"})
        self.assertEqual([row["id"] for row in response.data["results"]], [self.member_a.pk])
        response = self.client.post(
            "/api/v1/orders/",
            {
                "member": self.member_a.pk,
                "department": self.a.pk,
                "items": [{"item": self.catalog_item.pk, "quantity": 1}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNotNone(Order.objects.get(pk=response.data["id"]).items.first().status_id)

    def test_inventory_role_can_post_compensating_movement(self):
        self.use_role("inventory_manager")
        book_opening_stock(self.location, 3, item=self.item)
        opening = Transaction.objects.get(item=self.item, target=self.location)
        response = self.client.post(
            f"/api/v1/inventory/transactions/{opening.pk}/reverse/", {"reason": "Synthetic correction"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Stock.objects.get(item=self.item, location=self.location).quantity, 0)

    def test_lookup_does_not_reveal_shared_members_foreign_department_ids(self):
        self.member_a.departments.add(self.b)
        self.use_role("inventory_manager")
        row = self.client.get("/api/v1/role-member-options/", {"purpose": "inventory"}).data["results"][0]
        self.assertEqual(row["department_ids"], [self.a.pk])
