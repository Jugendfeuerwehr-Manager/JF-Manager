from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from qualifications.hierarchy import find_cycle, satisfying_types
from qualifications.models import QualificationType

User = get_user_model()


class ChainMixin:
    @classmethod
    def build_chain(cls):
        cls.truppmann = QualificationType.objects.create(name="Truppmann")
        cls.truppfuehrer = QualificationType.objects.create(name="Truppführer")
        cls.gruppenfuehrer = QualificationType.objects.create(name="Gruppenführer")
        cls.zugfuehrer = QualificationType.objects.create(name="Zugführer")
        cls.truppfuehrer.includes.add(cls.truppmann)
        cls.gruppenfuehrer.includes.add(cls.truppfuehrer)
        cls.zugfuehrer.includes.add(cls.gruppenfuehrer)


class HierarchyTests(ChainMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_chain()

    def test_closure_over_three_levels_in_one_query(self):
        with self.assertNumQueries(1):
            closure = satisfying_types()
        self.assertEqual(
            closure[self.truppmann.pk],
            {self.truppmann.pk, self.truppfuehrer.pk, self.gruppenfuehrer.pk, self.zugfuehrer.pk},
        )
        self.assertEqual(
            closure[self.truppfuehrer.pk], {self.truppfuehrer.pk, self.gruppenfuehrer.pk, self.zugfuehrer.pk}
        )
        self.assertNotIn(self.zugfuehrer.pk, closure)

    def test_find_cycle(self):
        self.assertTrue(find_cycle(self.truppmann.pk, [self.zugfuehrer.pk]))
        self.assertTrue(find_cycle(self.truppmann.pk, [self.truppmann.pk]))
        self.assertFalse(find_cycle(self.zugfuehrer.pk, [self.truppmann.pk]))


class ApiTests(ChainMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_chain()
        cls.admin = User.objects.create_superuser("root", "r@example.org", "pw")
        cls.reader = User.objects.create_user("reader", password="pw")
        cls.reader.user_permissions.add(Permission.objects.get(codename="view_qualificationtype"))

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def detail(self, obj):
        return reverse("qualification-types-detail", args=[obj.pk])

    def test_read_exposes_ids_and_names(self):
        body = self.client_for(self.reader).get(self.detail(self.truppfuehrer)).json()
        self.assertEqual(body["includes"], [self.truppmann.pk])
        self.assertEqual(body["includes_detail"], [{"id": self.truppmann.pk, "name": "Truppmann"}])

    def test_create_and_update_with_includes(self):
        client = self.client_for(self.admin)
        res = client.post(
            reverse("qualification-types-list"),
            {"name": "Sprechfunk 2", "includes": [self.truppmann.pk]},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["includes"], [self.truppmann.pk])
        res = client.patch(self.detail(self.zugfuehrer), {"includes": []}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["includes"], [])

    def test_write_requires_permission(self):
        res = self.client_for(self.reader).patch(self.detail(self.zugfuehrer), {"includes": []}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_self_reference_rejected(self):
        res = self.client_for(self.admin).patch(
            self.detail(self.truppmann), {"includes": [self.truppmann.pk]}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("nicht selbst", res.json()["includes"][0])

    def test_cycle_rejected(self):
        res = self.client_for(self.admin).patch(
            self.detail(self.truppmann), {"includes": [self.zugfuehrer.pk]}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Zyklische Zuordnung", res.json()["includes"][0])
        self.assertFalse(self.truppmann.includes.exists())
