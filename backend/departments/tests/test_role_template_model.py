from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from departments.models import RoleTemplate


class RoleTemplateModelTests(TestCase):
    def test_template_describes_group_without_modifying_its_permissions(self):
        group = Group.objects.create(name="Existing custom group")
        template = RoleTemplate.objects.create(
            key="inventory_manager",
            group=group,
            name="Inventarverwaltung",
            description="Verwaltet Material im zugewiesenen Bereich.",
            template_version=2,
            scope=RoleTemplate.Scope.BOTH,
            is_delegable=True,
        )

        self.assertEqual(template.group_id, group.pk)
        self.assertEqual(template.template_version, 2)
        self.assertEqual(template.scope, "both")
        self.assertEqual(group.permissions.count(), 0)

    def test_key_is_unique_and_cannot_be_renamed(self):
        template = RoleTemplate.objects.create(key="youth_leader", name="Jugendleiter", scope="department")
        with self.assertRaises(ValidationError):
            RoleTemplate.objects.create(key="youth_leader", name="Andere Anzeige", scope="department")

        template.key = "renamed_role"
        with self.assertRaises(ValidationError):
            template.save()
        template.refresh_from_db()
        self.assertEqual(template.key, "youth_leader")

    def test_invalid_key_scope_and_version_are_rejected(self):
        for overrides in (
            {"key": "UpperCase"},
            {"key": "with-hyphen"},
            {"scope": "unknown"},
            {"template_version": 0},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                RoleTemplate.objects.create(
                    key=overrides.get("key", "valid_key"),
                    name="Role",
                    scope=overrides.get("scope", "department"),
                    template_version=overrides.get("template_version", 1),
                )

    def test_group_binding_is_unique_and_group_cannot_be_deleted(self):
        group = Group.objects.create(name="Bound group")
        RoleTemplate.objects.create(key="first", group=group, name="First", scope="organization")
        with self.assertRaises(ValidationError):
            RoleTemplate.objects.create(key="second", group=group, name="Second", scope="organization")
        with self.assertRaises(IntegrityError), transaction.atomic():
            group.delete()

    def test_display_names_are_not_used_as_identity(self):
        first = RoleTemplate.objects.create(key="first", name="Gemeinsamer Name", scope="organization")
        second = RoleTemplate.objects.create(key="second", name="Gemeinsamer Name", scope="department")
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first.name, second.name)

    def test_database_enforces_key_uniqueness_even_without_model_validation(self):
        RoleTemplate.objects.create(key="first", name="First", scope="department")
        with self.assertRaises(IntegrityError), transaction.atomic():
            RoleTemplate.objects.bulk_create([RoleTemplate(key="first", name="Second", scope="organization")])
