"""Additional member fields: definitions API and values on the member. Fictional data."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from departments.models import Department
from members.models import Member, MemberFieldDefinition
from membership.tests.test_lifecycle import role

User = get_user_model()
URL = "/api/v1/member-fields/"
EDIT = ("view_memberfielddefinition", "add_memberfielddefinition", "change_memberfielddefinition")


class MemberFieldDefinitionApiTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="xf-mitte")
        self.nord = Department.objects.create(name="Nord", code="xf-nord")
        self.org_field = MemberFieldDefinition.objects.create(key="schule", label="Schule")
        self.nord_field = MemberFieldDefinition.objects.create(key="spind", label="Spind", department=self.nord)

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.get(URL).status_code, (401, 403))

    def test_staff_reads_own_and_organisation_fields_only(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_member"))
        keys = {row["key"] for row in self.client.get(URL).json()["results"]}
        self.assertEqual(keys, {"schule"})

    def test_missing_right_cannot_create(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_member"))
        response = self.client.post(URL, {"label": "Größe", "department": self.mitte.pk}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_foreign_department_and_organisation_scope_are_refused(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, *EDIT))
        for department in (self.nord.pk, None):
            response = self.client.post(URL, {"label": "Größe", "department": department}, format="json")
            self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(self.client.patch(f"{URL}{self.nord_field.pk}/", {"label": "x"}).status_code, 404)

    def test_editor_creates_a_choice_field_with_generated_key(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, *EDIT))
        response = self.client.post(
            URL,
            {
                "label": "T-Shirt-Größe",
                "department": self.mitte.pk,
                "field_type": "select",
                "options": [" 152 ", "164", "152", ""],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["key"], "t_shirt_groesse")
        self.assertEqual(response.json()["options"], ["152", "164"])

        field_id = response.json()["id"]
        response = self.client.patch(f"{URL}{field_id}/", {"field_type": "text"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_used_field_can_only_be_deactivated(self):
        user = self.user("leiter", self.mitte, *EDIT, "delete_memberfielddefinition")
        user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["can_access_all_departments", *EDIT, "delete_memberfielddefinition"]
            )
        )
        member = Member.objects.create(name="Mia", lastname="Muster", extra_fields={"schule": "Realschule"})
        member.departments.add(self.mitte)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.delete(f"{URL}{self.org_field.pk}/").status_code, 409)
        member.extra_fields = {}
        member.save()
        self.assertEqual(self.client.delete(f"{URL}{self.org_field.pk}/").status_code, 204)


class MemberExtraValueTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="xv-mitte")
        self.nord = Department.objects.create(name="Nord", code="xv-nord")
        MemberFieldDefinition.objects.create(key="groesse", label="Größe", field_type="select", options=["152", "164"])
        MemberFieldDefinition.objects.create(key="rad", label="Fahrrad", field_type="checkbox")
        MemberFieldDefinition.objects.create(key="spind", label="Spind", field_type="number", department=self.nord)
        self.member = Member.objects.create(name="Mia", lastname="Muster")
        self.member.departments.add(self.mitte)
        user = User.objects.create_user("leiter", password="x")
        role(user, self.mitte, "view_member", "change_member")
        self.client.force_authenticate(user)

    def patch(self, values):
        return self.client.patch(f"/api/v1/members/{self.member.pk}/", {"extra_fields": values}, format="json")

    def test_values_are_checked_merged_and_cleared(self):
        response = self.patch({"groesse": "152", "rad": True})
        self.assertEqual(response.status_code, 200, response.content)
        response = self.patch({"groesse": ""})
        self.assertEqual(response.status_code, 200, response.content)
        self.member.refresh_from_db()
        self.assertEqual(self.member.extra_fields, {"rad": True})

    def test_wrong_values_and_fields_of_other_departments_are_rejected(self):
        response = self.patch({"groesse": "999", "spind": 3, "unbekannt": "x"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["extra_fields"]), {"groesse", "spind", "unbekannt"})

    def test_member_form_sends_values_as_json_text(self):
        response = self.client.patch(
            f"/api/v1/members/{self.member.pk}/", {"extra_fields": '{"groesse": "164"}'}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.member.refresh_from_db()
        self.assertEqual(self.member.extra_fields, {"groesse": "164"})
