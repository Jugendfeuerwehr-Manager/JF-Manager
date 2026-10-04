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

    def test_change_right_in_a_does_not_allow_item_change_in_b(self):
        role_a = self.viewer.department_roles.get(department=self.line_a.order.department)
        role_a.groups.first().permissions.add(
            Permission.objects.get(content_type__app_label="orders", codename="change_orderitem")
        )

        response = self.client.patch(f"/api/v1/order-items/{self.line_b.pk}/", {"notes": "Changed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.line_b.refresh_from_db()
        self.assertEqual(self.line_b.notes, "")

    def test_status_right_without_org_scope_cannot_change_unassigned_b_item(self):
        self.viewer.user_permissions.add(
            Permission.objects.get(content_type__app_label="orders", codename="can_change_order_status")
        )
        self.viewer.department_roles.filter(department=self.line_b.order.department).delete()
        response = self.client.post(
            f"/api/v1/order-items/{self.line_b.pk}/update_status/",
            {"status": self.line_b.status_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_scoped_status_right_allows_a_item_but_not_b_item(self):
        role_a = self.viewer.department_roles.get(department=self.line_a.order.department)
        role_a.groups.first().permissions.add(
            Permission.objects.get(content_type__app_label="orders", codename="can_change_order_status")
        )

        allowed = self.client.post(
            f"/api/v1/order-items/{self.line_a.pk}/update_status/",
            {"status": self.line_a.status_id},
            format="json",
        )
        denied = self.client.post(
            f"/api/v1/order-items/{self.line_b.pk}/update_status/",
            {"status": self.line_b.status_id},
            format="json",
        )

        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_status_change_rejects_unassigned_b_item_without_partial_change(self):
        self.viewer.user_permissions.add(
            Permission.objects.get(content_type__app_label="orders", codename="can_change_order_status")
        )
        self.viewer.department_roles.filter(department=self.line_b.order.department).delete()
        response = self.client.post(
            "/api/v1/order-items/bulk_update_status/",
            {"item_ids": [self.line_a.pk, self.line_b.pk], "status": self.line_b.status_id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.line_a.refresh_from_db()
        self.line_b.refresh_from_db()
        self.assertEqual(self.line_a.status_id, self.line_b.status_id)
