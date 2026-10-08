from dataclasses import replace
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from departments.models import RoleTemplate
from departments.role_catalog import ROLE_SPECS


def run_seed(*args):
    output = StringIO()
    call_command("seed_role_templates", *args, stdout=output)
    return output.getvalue()


class SeedRoleTemplatesTests(TestCase):
    def test_catalog_has_separate_scope_variants_and_leadership_only_list_export(self):
        specs = {spec.key: spec for spec in ROLE_SPECS}
        self.assertEqual(len(specs), 16)
        self.assertIn("members.export_memberlist", specs["youth_director"].permissions)
        self.assertIn("members.export_memberlist", specs["department_youth_director"].permissions)
        self.assertNotIn("members.export_memberlist", specs["youth_leader"].permissions)
        self.assertNotIn("members.export_memberlist", specs["supervisor"].permissions)
        for spec in ROLE_SPECS:
            with self.subTest(key=spec.key):
                self.assertEqual(
                    "departments.can_access_all_departments" in spec.permissions,
                    spec.scope == "organization",
                )

    def test_seed_creates_each_role_once_without_assigning_users(self):
        output = run_seed()
        self.assertIn("16 neue Vorlagen", output)
        self.assertEqual(RoleTemplate.objects.count(), 16)
        self.assertEqual(Group.objects.filter(name__startswith="jf_role__").count(), 16)
        for spec in ROLE_SPECS:
            template = RoleTemplate.objects.select_related("group").get(key=spec.key)
            self.assertEqual(template.group.name, spec.group_name)
            self.assertEqual(
                {
                    f"{p.content_type.app_label}.{p.codename}"
                    for p in template.group.permissions.select_related("content_type")
                },
                set(spec.permissions),
            )
            self.assertFalse(template.group.user_set.exists())

        self.assertIn("0 neue Vorlagen", run_seed())
        self.assertEqual(RoleTemplate.objects.count(), 16)
        self.assertEqual(Group.objects.filter(name__startswith="jf_role__").count(), 16)

    def test_existing_customizations_are_reported_and_never_overwritten(self):
        run_seed()
        template = RoleTemplate.objects.get(key="youth_director")
        template.name = "Kundeneigener Name"
        template.save()
        extra_permission = Permission.objects.get(content_type__app_label="members", codename="delete_member")
        template.group.permissions.add(extra_permission)
        missing_permission = Permission.objects.get(content_type__app_label="members", codename="export_memberlist")
        template.group.permissions.remove(missing_permission)

        output = run_seed()
        self.assertIn("ABWEICHUNG youth_director", output)
        self.assertIn("members.export_memberlist", output)
        template.refresh_from_db()
        self.assertEqual(template.name, "Kundeneigener Name")
        self.assertTrue(template.group.permissions.filter(pk=extra_permission.pk).exists())
        self.assertFalse(template.group.permissions.filter(pk=missing_permission.pk).exists())

    def test_same_display_name_does_not_bind_an_existing_group(self):
        old_group = Group.objects.create(name="Jugendwart")
        run_seed()
        template = RoleTemplate.objects.get(key="youth_director")
        self.assertNotEqual(template.group_id, old_group.pk)
        self.assertEqual(old_group.permissions.count(), 0)

    def test_group_name_collision_aborts_all_creation(self):
        Group.objects.create(name="jf_role__youth_director")
        with self.assertRaisesMessage(CommandError, "keine Namensübernahme"):
            run_seed()
        self.assertEqual(RoleTemplate.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 1)

    def test_unbound_existing_template_is_reported_without_binding(self):
        template = RoleTemplate.objects.create(key="youth_director", name="Eigene Vorlage", scope="organization")
        output = run_seed()
        self.assertIn("ABWEICHUNG youth_director: keine Django-Gruppe gebunden", output)
        template.refresh_from_db()
        self.assertIsNone(template.group_id)
        self.assertFalse(Group.objects.filter(name="jf_role__youth_director").exists())

    def test_dry_run_and_missing_permission_leave_database_unchanged(self):
        self.assertIn("Trockenlauf", run_seed("--dry-run"))
        self.assertEqual(RoleTemplate.objects.count(), 0)
        missing_spec = replace(ROLE_SPECS[0], permissions=("members.permission_that_does_not_exist",))
        with (
            patch(
                "departments.management.commands.seed_role_templates.ROLE_SPECS",
                (missing_spec, *ROLE_SPECS[1:]),
            ),
            self.assertRaisesMessage(CommandError, "Fehlende Django-Permissions"),
        ):
            run_seed()
        self.assertEqual(RoleTemplate.objects.count(), 0)
