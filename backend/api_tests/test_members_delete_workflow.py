from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.models import Category, Item, StorageLocation, Transaction
from members.models import Member


class MemberDeleteWorkflowApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="member_delete_admin",
            email="member_delete_admin@example.com",
            password="pw12345",
        )
        self.client.force_authenticate(user=self.user)

        self.member = Member.objects.create(name="Lukas", lastname="Bisdorf")
        self.personal_storage = StorageLocation.objects.create(
            name="Personal Lukas Bisdorf",
            is_member=True,
            member=self.member,
        )

        category = Category.objects.create(name="Uniform")
        self.item = Item.objects.create(name="Uniform Jacke", category=category)

    def _create_transaction_for_member_storage(self):
        return Transaction.objects.create(
            transaction_type="IN",
            item=self.item,
            target=self.personal_storage,
            quantity=1,
            user=self.user,
        )

    def test_delete_member_returns_409_when_transactions_exist(self):
        self._create_transaction_for_member_storage()

        response = self.client.delete(f"/api/v1/members/{self.member.id}/")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"], "protected")
        self.assertEqual(response.data["transaction_count"], 1)
        self.assertEqual(response.data["member_name"], "Lukas Bisdorf")
        self.assertTrue(Member.objects.filter(id=self.member.id).exists())

    def test_delete_with_strategy_unlink_deletes_member_and_preserves_history(self):
        transaction = self._create_transaction_for_member_storage()

        response = self.client.post(
            f"/api/v1/members/{self.member.id}/delete-with-strategy/",
            {"strategy": "unlink"},
            format="json",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Member.objects.filter(id=self.member.id).exists())

        transaction.refresh_from_db()
        self.assertIsNone(transaction.source)
        self.assertIsNone(transaction.target)
        self.assertEqual(transaction.former_member_name, "Lukas Bisdorf")

    def test_delete_member_without_storage_relations(self):
        member = Member.objects.create(name="Ohne", lastname="Lager")

        response = self.client.delete(f"/api/v1/members/{member.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Member.objects.filter(id=member.id).exists())
