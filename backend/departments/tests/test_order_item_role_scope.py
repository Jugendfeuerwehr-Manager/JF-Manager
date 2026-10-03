"""Order items inherit the department of their order."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member
from orders.models import Order, OrderableItem, OrderItem, OrderStatus


class OrderItemRoleScopeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        department_a = Department.objects.create(name="A", code="order-item-a")
        department_b = Department.objects.create(name="B", code="order-item-b")
        member_a = Member.objects.create(name="A", lastname="Member")
        member_b = Member.objects.create(name="B", lastname="Member")
        member_a.departments.add(department_a)
        member_b.departments.add(department_b)
        item = OrderableItem.objects.create(name="Jacket", category="Clothing")
        order_status, _ = OrderStatus.objects.get_or_create(code="ORDERED", defaults={"name": "Ordered"})
        cls.line_a = OrderItem.objects.create(
            order=Order.objects.create(member=member_a, department=department_a), item=item, status=order_status
        )
        cls.line_b = OrderItem.objects.create(
            order=Order.objects.create(member=member_b, department=department_b), item=item, status=order_status
        )
        cls.viewer = get_user_model().objects.create_user(username="order-item-viewer", password="test-only-password")
        group_a = Group.objects.create(name="Order item viewer A")
        group_a.permissions.add(Permission.objects.get(content_type__app_label="orders", codename="view_orderitem"))
        UserDepartmentRole.objects.create(user=cls.viewer, department=department_a).groups.add(group_a)
        UserDepartmentRole.objects.create(user=cls.viewer, department=department_b)

    def setUp(self):
        self.client.force_authenticate(user=self.viewer)

    def test_order_item_list_contains_only_permitted_department(self):
        response = self.client.get("/api/v1/order-items/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual({row["id"] for row in rows}, {self.line_a.pk})

    def test_order_item_detail_in_read_only_department_is_hidden(self):
        response = self.client.get(f"/api/v1/order-items/{self.line_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
