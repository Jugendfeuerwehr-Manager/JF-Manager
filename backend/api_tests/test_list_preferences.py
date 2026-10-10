"""UX-02.3: saved list filters per user and department, never search texts."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from departments.models import Department
from users.models import ListPreference

URL = "/api/v1/list-preferences/"
User = get_user_model()


class ListPreferenceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("leitung", password="x")
        self.other = User.objects.create_user("andere", password="x")
        self.dept = Department.objects.create(name="Mitte", code="lp-mitte")
        self.client.force_authenticate(self.user)

    def save(self, data, department=None, view="members"):
        return self.client.post(URL, {"view": view, "department": department, "data": data}, format="json")

    def test_saves_and_reads_own_filters_per_department(self):
        self.assertEqual(
            self.save({"status": 2, "rows": 50, "sortField": "firstname", "sortOrder": -1}, self.dept.pk).status_code,
            200,
        )
        self.assertEqual(self.save({"group": 4}).status_code, 200)
        scoped = self.client.get(URL, {"view": "members", "department": self.dept.pk}).json()
        self.assertEqual(scoped["data"], {"status": 2, "rows": 50, "sortField": "firstname", "sortOrder": -1})
        self.assertEqual(self.client.get(URL, {"view": "members"}).json()["data"], {"group": 4})
        self.assertEqual(self.save({"status": 3}, self.dept.pk).status_code, 200)
        self.assertEqual(ListPreference.objects.filter(user=self.user).count(), 2)

    def test_search_texts_and_unknown_keys_are_never_stored(self):
        response = self.save({"search": "Mia Beispiel", "status": 1})
        self.assertEqual(response.status_code, 400)
        self.assertIn("search", str(response.json()))
        self.assertFalse(ListPreference.objects.exists())

    def test_invalid_values_and_views_are_rejected(self):
        self.assertEqual(self.save({"rows": 7}).status_code, 400)
        self.assertEqual(self.save({"sortField": "name; drop"}).status_code, 400)
        self.assertEqual(self.save({"status": True}).status_code, 400)
        self.assertEqual(self.save({}, view="secret").status_code, 400)
        self.assertEqual(self.save({}, department=999999).status_code, 400)
        self.assertEqual(self.client.get(URL, {"view": "secret"}).status_code, 400)

    def test_preferences_stay_private_to_their_account(self):
        self.save({"status": 2})
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(URL, {"view": "members"}).json()["data"], {})

    def test_requires_login_and_a_staff_account(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(URL, {"view": "members"}).status_code, (401, 403))
        portal = User.objects.create_user("eltern", password="x", account_kind=User.AccountKind.PORTAL)
        self.client.force_authenticate(portal)
        self.assertEqual(self.client.get(URL, {"view": "members"}).status_code, 403)
        self.assertEqual(self.save({"status": 2}).status_code, 403)
