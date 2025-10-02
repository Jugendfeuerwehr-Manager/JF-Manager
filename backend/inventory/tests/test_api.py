import json
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from inventory.models import Category, Item, StorageLocation, Stock


class InventoryAPITest(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pw12345")
        self.client = APIClient()
        self.client.login(username="tester", password="pw12345")
        self.category = Category.objects.create(name="Helm")
        self.item = Item.objects.create(name="Helm A", category=self.category)
        self.location = StorageLocation.objects.create(name="Lager 1")
        Stock.objects.create(item=self.item, location=self.location, quantity=5)

    def test_list_items(self):
        url = "/api/v1/inventory/items/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data['results']), 1)

    def test_item_stock_action(self):
        url = f"/api/v1/inventory/items/{self.item.id}/stock/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['total'], 5)
