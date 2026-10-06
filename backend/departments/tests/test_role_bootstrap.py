from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase, override_settings

from departments.models import RoleTemplate
from departments.role_catalog import ROLE_SPECS


@override_settings(ROLE_SEED_ON_MIGRATE=True)
class RoleBootstrapTests(TestCase):
    def test_migrate_installs_every_standard_role_and_never_assigns_accounts(self):
        user = get_user_model().objects.create_user(username="bootstrap-staff", is_staff=True)
        call_command("migrate", verbosity=0, stdout=StringIO())
        self.assertEqual(set(RoleTemplate.objects.values_list("key", flat=True)), {spec.key for spec in ROLE_SPECS})
        self.assertFalse(user.groups.exists())
        self.assertFalse(user.department_roles.exists())
        call_command("migrate", verbosity=0, stdout=StringIO())
        self.assertEqual(RoleTemplate.objects.count(), 16)

    def test_migrate_restores_missing_templates_and_preserves_customized_rights(self):
        call_command("seed_role_templates", stdout=StringIO())
        template = RoleTemplate.objects.get(key="supervisor")
        extra = Permission.objects.get(content_type__app_label="members", codename="export_member")
        template.group.permissions.add(extra)
        missing = RoleTemplate.objects.get(key="order_manager")
        group = missing.group
        missing.delete()
        group.delete()
        call_command("migrate", verbosity=0, stdout=StringIO())
        self.assertEqual(RoleTemplate.objects.count(), 16)
        self.assertTrue(template.group.permissions.filter(pk=extra.pk).exists())
