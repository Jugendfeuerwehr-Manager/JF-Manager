"""UX-02.2a: the member list filters by exact birthday for the duplicate hint. Fictional data."""

from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from members.models import Member


class MemberBirthdayFilterTests(APITestCase):
    def test_filters_by_exact_birthday(self):
        admin = get_user_model().objects.create_superuser(username="org", password="Org!12345")
        Member.objects.create(
            name="Mia", lastname="Beispiel", birthday=date(2012, 5, 3), gender="female", joined=date(2020, 1, 1)
        )
        Member.objects.create(
            name="Mia", lastname="Beispiel", birthday=date(2013, 5, 3), gender="female", joined=date(2020, 1, 1)
        )
        self.client.force_authenticate(admin)
        response = self.client.get("/api/v1/members/?search=Beispiel&birthday=2012-05-03")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["birthday"] for row in response.data["results"]], ["2012-05-03"])
