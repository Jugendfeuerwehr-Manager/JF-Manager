"""Organization catalogs must not become writable through scoped staff roles."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from orders.models import OrderableItem, OrderStatus


class GlobalCatalogWriteRoleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        department = Department.objects.create(name="A", code="global-catalog-a")
        cls.staff = get_user_model().objects.create_user(username="catalog-staff", is_staff=True)
        group = Group.objects.create(name="Scoped catalog editor A")
        for codename in ("add_orderstatus", "add_orderableitem"):
            group.permissions.add(
                Permission.objects.get(content_type__app_label="orders", codename=codename)
            )
        UserDepartmentRole.objects.create(user=cls.staff, department=department).groups.add(group)

    def setUp(self):
        self.client.force_authenticate(user=self.staff)

    def test_staff_with_scoped_right_cannot_create_global_order_status(self):
        response = self.client.post(
            "/api/v1/order-statuses/", {"name": "New status", "code": "NEW-GLOBAL"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(OrderStatus.objects.filter(code="NEW-GLOBAL").exists())

    def test_staff_with_scoped_right_cannot_create_global_order_catalog_item(self):
        response = self.client.post(
            "/api/v1/orderable-items/", {"name": "Global jacket", "category": "Clothing"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(OrderableItem.objects.filter(name="Global jacket").exists())
