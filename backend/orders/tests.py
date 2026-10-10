"""UX-05.1: status history per order, read through the department-scoped order API."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from inventory.models import Category, Item
from members.models import Member
from orders.models import Order, OrderableItem, OrderItem, OrderStatus


class OrderStatusHistoryTests(APITestCase):
    def setUp(self):
        self.dept_a = Department.objects.create(name="Abteilung A", code="ux05-orders-a")
        self.dept_b = Department.objects.create(name="Abteilung B", code="ux05-orders-b")
        self.user = self.department_user(
            "order-clerk", self.dept_a, ["view_order", "view_orderitem", "change_orderitem", "can_change_order_status"]
        )
        self.client.force_authenticate(self.user)
        item = Item.objects.create(name="Helm", category=Category.objects.create(name="Ausrüstung"))
        orderable = OrderableItem.objects.get(inventory_item=item)
        member = Member.objects.create(name="Alex", lastname="Synthetisch")
        self.order = Order.objects.create(member=member, department=self.dept_a, ordered_by=self.user)
        self.line = OrderItem.objects.create(
            order=self.order, item=orderable, quantity=1, status=OrderStatus.objects.get(code="NEW")
        )
        self.foreign_order = Order.objects.create(member=member, department=self.dept_b)

    def department_user(self, username, department, codenames):
        user = get_user_model().objects.create_user(username=username, password="pw12345")
        group = Group.objects.create(name=f"{username}-role")
        group.permissions.set(Permission.objects.filter(codename__in=codenames))
        role = UserDepartmentRole.objects.create(user=user, department=department)
        role.groups.add(group)
        return user

    def test_workflow_change_appears_in_order_history(self):
        ordered = OrderStatus.objects.get(code="ORDERED")
        change = self.client.post(f"/api/v1/order-items/{self.line.pk}/update_status/", {"status": ordered.pk})
        self.assertEqual(change.status_code, 200, change.data)

        response = self.client.get(f"/api/v1/orders/{self.order.pk}/detail_with_history/")

        self.assertEqual(response.status_code, 200, response.data)
        history = response.data["items"][0]["history"]
        self.assertEqual(
            [(entry["old_status_name"], entry["new_status_name"]) for entry in history],
            [(self.line.status.name, ordered.name)],
        )
        self.assertEqual(history[0]["changed_by"], self.user.pk)

    def test_rejected_transition_leaves_history_unchanged(self):
        delivered = OrderStatus.objects.get(code="DELIVERED")
        change = self.client.post(f"/api/v1/order-items/{self.line.pk}/update_status/", {"status": delivered.pk})
        self.assertEqual(change.status_code, 400)
        response = self.client.get(f"/api/v1/orders/{self.order.pk}/detail_with_history/")
        self.assertEqual(response.data["items"][0]["history"], [])

    def test_foreign_department_and_missing_rights_cannot_read_history(self):
        self.assertEqual(
            self.client.get(f"/api/v1/orders/{self.foreign_order.pk}/detail_with_history/").status_code, 404
        )
        self.client.force_authenticate(self.department_user("no-orders", self.dept_a, []))
        self.assertIn(self.client.get(f"/api/v1/orders/{self.order.pk}/detail_with_history/").status_code, (403, 404))
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(f"/api/v1/orders/{self.order.pk}/detail_with_history/").status_code, (401, 403))
