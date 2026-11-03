"""DSGVO need-to-know: field rights, health notes behind step-up, minimal disclosure. Fictional data."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import override_settings
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import ExportAudit, Member
from users import mfa

User = get_user_model()


def role(user, department, *codenames):
    group = Group.objects.create(name=f"{user.username}-{department.code}")
    group.permissions.add(*Permission.objects.filter(content_type__app_label="members", codename__in=codenames))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class FieldRightTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="ntk-mitte")
        self.member = Member.objects.create(
            name="Mia",
            lastname="Muster",
            street="Musterweg 1",
            phone="0123",
            notes="Vertraulich",
            identityCardNumber="JF-1",
            health_notes="Allergie",
        )
        self.member.departments.add(self.mitte)
        self.url = f"/api/v1/members/{self.member.pk}/"

    def user(self, name, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, self.mitte, *codenames)
        return user

    def test_reader_sees_name_but_no_contact_sensitive_or_health_data(self):
        self.client.force_authenticate(self.user("betreuer", "view_member"))
        data = self.client.get(self.url).json()
        self.assertEqual(data["name"], "Mia")
        for field in ("street", "phone", "email", "notes", "identityCardNumber", "canSwimm", "has_health_notes"):
            self.assertNotIn(field, data)
        self.assertNotIn("health_notes", data)
        row = self.client.get("/api/v1/members/").json()["results"][0]
        self.assertNotIn("phone", row)

    def test_field_rights_reveal_their_fields(self):
        self.client.force_authenticate(
            self.user("leitung", "view_member", "view_member_contact", "view_member_sensitive", "view_member_health")
        )
        data = self.client.get(self.url).json()
        self.assertEqual((data["street"], data["notes"]), ("Musterweg 1", "Vertraulich"))
        self.assertTrue(data["has_health_notes"])
        self.assertNotIn("health_notes", data)  # never with the member, only via its own endpoint

    def test_writes_to_hidden_fields_are_ignored(self):
        self.client.force_authenticate(self.user("schreiber", "view_member", "change_member"))
        response = self.client.patch(self.url, {"notes": "", "street": "", "name": "Mia-Sophie"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        member = Member.objects.get(pk=self.member.pk)
        self.assertEqual((member.name, member.notes, member.street), ("Mia-Sophie", "Vertraulich", "Musterweg 1"))

    def test_health_notes_are_encrypted_at_rest(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT health_notes FROM members_member WHERE id = %s", [self.member.pk])
            raw = cursor.fetchone()[0]
        self.assertNotIn("Allergie", raw)


class HealthEndpointTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="health-mitte")
        self.nord = Department.objects.create(name="Nord", code="health-nord")
        self.member = Member.objects.create(name="Mia", lastname="Muster", health_notes="Allergie: Wespenstich")
        self.member.departments.add(self.mitte)
        self.url = f"/api/v1/members/{self.member.pk}/health/"

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_without_health_right_nothing_is_disclosed(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_member", "view_member_contact"))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Allergie", response.content.decode())

    def test_foreign_department_cannot_reach_the_member(self):
        self.client.force_authenticate(self.user("nord", self.nord, "view_member", "view_member_health"))
        self.assertEqual(self.client.get(self.url).status_code, 404)

    # Session test about scope/step-up, not MFA (covered in privacy.tests.test_hardening).

    @override_settings(MFA_REQUIRED_FOR_MEMBER_DATA=False)
    def test_every_disclosure_needs_a_fresh_confirmation_and_is_logged(self):
        user = self.user("betreuer", self.mitte, "view_member", "view_member_health")
        self.client.force_login(user)
        session = self.client.session
        session[mfa.REAUTH_KEY] = 0
        session.save()
        stale = self.client.get(self.url)
        self.assertEqual(stale.status_code, 403)
        self.assertEqual(stale.json()["code"], "reauthentication_required")
        self.assertFalse(ExportAudit.objects.exists())

        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["health_notes"], "Allergie: Wespenstich")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(ExportAudit.objects.get().action, "health_view")

    def test_changing_needs_the_change_right_too(self):
        reader = self.user("betreuer", self.mitte, "view_member", "view_member_health")
        self.client.force_authenticate(reader)
        self.assertEqual(self.client.put(self.url, {"health_notes": "x"}, format="json").status_code, 403)
        editor = self.user("leitung", self.mitte, "view_member", "change_member", "view_member_health")
        self.client.force_authenticate(editor)
        response = self.client.put(self.url, {"health_notes": "Asthma-Spray"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Member.objects.get(pk=self.member.pk).health_notes, "Asthma-Spray")
        self.assertTrue(ExportAudit.objects.filter(action="health_change").exists())


class CoParentConsentTests(APITestCase):
    def test_other_parent_contact_only_with_opt_in(self):
        from members.models import Parent
        from portal.disclosure import _other_parents

        child = Member.objects.create(name="Mia", lastname="Muster")
        viewer = Parent.objects.create(name="Eva", lastname="Muster")
        other = Parent.objects.create(name="Tom", lastname="Muster", phone="0170")
        viewer.children.add(child)
        other.children.add(child)
        self.assertEqual(_other_parents(child, viewer), [])
        other.share_contact_with_coparent = True
        other.save()
        self.assertEqual(_other_parents(child, viewer)[0]["phone"], "0170")


class OrderExportAuditTests(APITestCase):
    def test_csv_export_is_audited(self):
        admin = User.objects.create_superuser("admin", password="x")
        self.client.force_authenticate(admin)
        response = self.client.get("/api/v1/orders/export/")
        self.assertEqual(response.status_code, 200)
        audit = ExportAudit.objects.get()
        self.assertEqual((audit.action, audit.object_type), ("export", "orders.order"))
