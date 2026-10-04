"""Inventory writes must validate the departments of linked targets."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from inventory.models import Category, Item, ItemVariant, StorageLocation
from members.models import Member


class InventoryTargetRelationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="inventory-target-a")
        cls.department_b = Department.objects.create(name="B", code="inventory-target-b")
        category = Category.objects.create(name="Equipment")
        cls.item_a = Item.objects.create(name="A item", category=category, department=cls.department_a)
        cls.item_b = Item.objects.create(name="B item", category=category, department=cls.department_b)
        cls.variant_a = ItemVariant.objects.create(parent_item=cls.item_a, variant_attributes={"size": "a"})
        cls.location_b = StorageLocation.objects.create(name="B shelf", department=cls.department_b)
        cls.member_b = Member.objects.create(name="B", lastname="Member")
        cls.member_b.departments.add(cls.department_b)

        cls.user = get_user_model().objects.create_user(username="inventory-target-writer")
        writer = AuthGroup.objects.create(name="Inventory target writer A")
        writer.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="inventory",
                codename__in=["add_item", "add_itemvariant", "change_itemvariant", "add_storagelocation"],
            )
        )
        reader = AuthGroup.objects.create(name="Inventory target reader B")
        reader.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="inventory",
                codename__in=["view_item", "view_itemvariant", "view_storagelocation"],
            )
        )
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_a).groups.add(writer)
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_b).groups.add(reader)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_variant_cannot_be_created_for_read_only_parent(self):
        response = self.client.post(
            "/api/v1/inventory/variants/",
            {"parent_item": self.item_b.pk, "variant_attributes": {"size": "foreign"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ItemVariant.objects.filter(parent_item=self.item_b).exists())

    def test_variant_cannot_be_moved_to_read_only_parent(self):
        response = self.client.patch(
            f"/api/v1/inventory/variants/{self.variant_a.pk}/",
            {"parent_item": self.item_b.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.variant_a.refresh_from_db()
        self.assertEqual(self.variant_a.parent_item_id, self.item_a.pk)

    def test_location_cannot_link_read_only_parent(self):
        response = self.client.post(
            "/api/v1/inventory/locations/",
            {"name": "A child", "department": self.department_a.pk, "parent": self.location_b.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(StorageLocation.objects.filter(name="A child").exists())

    def test_location_cannot_link_member_from_read_only_department(self):
        response = self.client.post(
            "/api/v1/inventory/locations/",
            {"name": "B personal", "department": self.department_a.pk, "is_member": True, "member": self.member_b.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(StorageLocation.objects.filter(name="B personal").exists())

    def test_item_cannot_link_member_from_read_only_department(self):
        response = self.client.post(
            "/api/v1/inventory/items/",
            {
                "name": "A linked item",
                "category": self.item_a.category_id,
                "department": self.department_a.pk,
                "rented_by": self.member_b.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Item.objects.filter(name="A linked item").exists())

    def test_variant_can_be_created_for_writable_parent(self):
        response = self.client.post(
            "/api/v1/inventory/variants/",
            {"parent_item": self.item_a.pk, "variant_attributes": {"size": "own"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ItemVariant.objects.filter(parent_item=self.item_a, variant_attributes={"size": "own"}).exists())

    def test_location_can_link_writable_parent(self):
        parent_a = StorageLocation.objects.create(name="A shelf", department=self.department_a)
        response = self.client.post(
            "/api/v1/inventory/locations/",
            {"name": "A child", "department": self.department_a.pk, "parent": parent_a.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(StorageLocation.objects.filter(name="A child", parent=parent_a).exists())
