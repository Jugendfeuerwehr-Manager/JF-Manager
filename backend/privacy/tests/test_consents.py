"""DSGVO: consents are append-only evidence, scoped like the person they belong to. Fictional data."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent
from privacy.models import ConsentRecord
from privacy.services.consent import current_consents, has_consent

User = get_user_model()
BASE = "/api/v1/privacy/consents/"


def role(user, department, *codenames):
    group = Group.objects.create(name=f"{user.username}-{department.code}")
    group.permissions.add(*Permission.objects.filter(codename__in=codenames))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class ConsentApiTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="consent-mitte")
        self.nord = Department.objects.create(name="Nord", code="consent-nord")
        self.member = Member.objects.create(name="Mia", lastname="Beispiel")
        self.member.departments.add(self.mitte)
        self.parent = Parent.objects.create(name="Eva", lastname="Beispiel")
        self.parent.children.add(self.member)
        self.leader = User.objects.create_user("leitung", password="x")
        role(self.leader, self.mitte, "view_member", "change_member", "view_parent")
        self.reader = User.objects.create_user("betreuer", password="x")
        role(self.reader, self.mitte, "view_member")
        self.foreign = User.objects.create_user("nord", password="x")
        role(self.foreign, self.nord, "view_member", "change_member")

    def grant(self, **overrides):
        data = {"member": self.member.pk, "kind": "photo_internal", "status": "granted", **overrides}
        return self.client.post(BASE, data, format="json")

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.get(f"{BASE}?member={self.member.pk}").status_code, (401, 403))
        self.assertIn(self.grant().status_code, (401, 403))

    def test_read_right_lists_but_cannot_record(self):
        ConsentRecord.objects.create(member=self.member, kind="photo_public", status="granted", source="staff")
        self.client.force_authenticate(self.reader)
        response = self.client.get(f"{BASE}?member={self.member.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["kind_label"], "Fotos öffentlich (Website, Presse, soziale Medien)")
        self.assertEqual(self.grant().status_code, 403)
        # Without the parent read right the parent is not even visible.
        self.assertEqual(self.client.get(f"{BASE}?parent={self.parent.pk}").status_code, 404)

    def test_foreign_department_sees_nothing(self):
        self.client.force_authenticate(self.foreign)
        self.assertEqual(self.client.get(f"{BASE}?member={self.member.pk}").status_code, 404)
        self.assertEqual(self.grant().status_code, 404)

    def test_leader_records_and_withdraws_as_new_rows(self):
        self.client.force_authenticate(self.leader)
        created = self.grant(note="Formular vom 01.10.")
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual((created.json()["source"], created.json()["recorded_by_name"]), ("staff", "leitung"))
        self.assertTrue(has_consent(self.member, "photo_internal"))
        self.assertEqual(self.grant(status="withdrawn").status_code, 201)
        self.assertFalse(has_consent(self.member, "photo_internal"))
        self.assertEqual(ConsentRecord.objects.filter(member=self.member).count(), 2)
        self.assertEqual(current_consents(self.member)["photo_internal"].status, "withdrawn")

    def test_subject_and_kind_are_validated(self):
        self.client.force_authenticate(self.leader)
        self.assertEqual(self.client.get(BASE).status_code, 400)
        both = self.grant(parent=self.parent.pk)
        self.assertEqual(both.status_code, 400)
        self.assertEqual(self.grant(kind="unknown").status_code, 400)

    def test_account_consents_need_user_administration(self):
        self.client.force_authenticate(self.leader)
        self.assertEqual(self.client.get(f"{BASE}?user={self.reader.pk}").status_code, 403)
        self.assertEqual(self.client.get(f"{BASE}?user={self.leader.pk}").status_code, 200)  # own consents
        admin = User.objects.create_user("admin", password="x")
        admin.user_permissions.add(*Permission.objects.filter(codename__in=["view_customuser", "change_customuser"]))
        self.client.force_authenticate(admin)
        response = self.client.post(
            BASE, {"user": self.reader.pk, "kind": "confidentiality", "status": "granted"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)


class FlagMigrationTests(APITestCase):
    def test_carry_over_creates_import_rows(self):
        from importlib import import_module
        from types import SimpleNamespace

        from django.apps import apps

        migration = import_module("users.migrations.0015_dsgvo_flags_to_consents")
        user = User.objects.create_user("alt", password="x")

        class HistoricalUsers:
            # The flag columns are gone in the current schema; emulate one flagged account.
            def filter(self, **flags):
                return User.objects.filter(pk=user.pk) if flags.get("dsgvo_external") else User.objects.none()

        def get_model(app, model):
            return SimpleNamespace(objects=HistoricalUsers()) if model == "CustomUser" else apps.get_model(app, model)

        migration.flags_to_consents(SimpleNamespace(get_model=get_model), None)
        record = ConsentRecord.objects.get(user=user)
        self.assertEqual((record.kind, record.source, record.status), ("dsgvo_external", "import", "granted"))
