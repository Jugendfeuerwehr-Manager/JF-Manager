import re
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from departments.models import Department, RoleTemplate, UserDepartmentRole
from settings_manager.models import OIDCConfig, OIDCGroupMapping


def run_reconcile(*args, **options):
    output = StringIO()
    call_command("reconcile_role_groups", *args, stdout=output, **options)
    return output.getvalue()


def fingerprint(output):
    return re.search(r"Fingerprint: ([0-9a-f]{64})", output).group(1)


class ReconcileRoleGroupsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.department = Department.objects.create(name="Testabteilung", code="role-test")
        cls.user = get_user_model().objects.create_user(username="legacy-role-user")
        cls.staff = get_user_model().objects.create_user(username="unassigned-staff", is_staff=True)

    def _legacy_group(self, *, organization_scope=False):
        group = Group.objects.create(name="Jugendleiter")
        group.permissions.add(Permission.objects.get(content_type__app_label="members", codename="view_member"))
        if organization_scope:
            group.permissions.add(
                Permission.objects.get(content_type__app_label="departments", codename="can_access_all_departments")
            )
        role = UserDepartmentRole.objects.create(user=self.user, department=self.department)
        role.groups.add(group)
        return group, role

    def test_audit_and_compare_are_read_only_and_show_assignments(self):
        group, role = self._legacy_group()
        original_group_id = RoleTemplate.objects.get(key="youth_leader").group_id
        audit = run_reconcile()
        self.assertIn(f"Gruppe {group.pk} 'Jugendleiter'", audit)
        self.assertIn(f"({role.pk}, {self.user.pk}, {self.department.pk})", audit)
        comparison = run_reconcile(template_key="youth_leader", group_id=group.pk)
        self.assertIn("Fehlende Permissions:", comparison)
        self.assertIn("Fingerprint:", comparison)
        self.assertEqual(RoleTemplate.objects.get(key="youth_leader").group_id, original_group_id)
        self.assertFalse(self.staff.groups.exists())

    def test_explicit_binding_preserves_permissions_assignments_and_staff_state(self):
        group, role = self._legacy_group()
        template = RoleTemplate.objects.get(key="youth_leader")
        previous_group_id = template.group_id
        original_permissions = set(group.permissions.values_list("pk", flat=True))
        token = fingerprint(run_reconcile(template_key="youth_leader", group_id=group.pk))

        result = run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True, expected=token)
        self.assertIn("verbunden", result)
        template.refresh_from_db()
        self.assertEqual(template.group_id, group.pk)
        self.assertTrue(Group.objects.filter(pk=previous_group_id).exists())
        self.assertEqual(set(group.permissions.values_list("pk", flat=True)), original_permissions)
        self.assertTrue(role.groups.filter(pk=group.pk).exists())
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_staff)
        self.assertFalse(self.staff.groups.exists())
        self.assertFalse(self.staff.is_superuser)

    def test_stale_fingerprint_rejects_changed_permissions(self):
        group, _ = self._legacy_group()
        original_group_id = RoleTemplate.objects.get(key="youth_leader").group_id
        token = fingerprint(run_reconcile(template_key="youth_leader", group_id=group.pk))
        group.permissions.add(Permission.objects.get(content_type__app_label="members", codename="export_memberlist"))
        with self.assertRaisesMessage(CommandError, "Zustand seit dem Vergleich geändert"):
            run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True, expected=token)
        self.assertEqual(RoleTemplate.objects.get(key="youth_leader").group_id, original_group_id)

    def test_assigned_seed_group_cannot_be_replaced(self):
        group, _ = self._legacy_group()
        template = RoleTemplate.objects.get(key="youth_leader")
        template.group.user_set.add(self.staff)
        token = fingerprint(run_reconcile(template_key="youth_leader", group_id=group.pk))
        with self.assertRaisesMessage(CommandError, "Bisherige Vorlagengruppe hat Zuweisungen"):
            run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True, expected=token)
        template.refresh_from_db()
        self.assertNotEqual(template.group_id, group.pk)
        self.assertTrue(self.staff.groups.filter(pk=template.group_id).exists())

    def test_scope_conflicts_are_rejected(self):
        group, _ = self._legacy_group(organization_scope=True)
        token = fingerprint(run_reconcile(template_key="youth_leader", group_id=group.pk))
        with self.assertRaisesMessage(CommandError, "Organisationsberechtigung passt nicht"):
            run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True, expected=token)

    def test_global_user_assignment_cannot_be_labeled_department_scope(self):
        group, _ = self._legacy_group()
        group.user_set.add(self.user)
        token = fingerprint(run_reconcile(template_key="youth_leader", group_id=group.pk))
        with self.assertRaisesMessage(CommandError, "global zugewiesene Gruppe"):
            run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True, expected=token)

    def test_group_bound_to_another_template_cannot_be_reused(self):
        group = RoleTemplate.objects.get(key="supervisor").group
        token = fingerprint(run_reconcile(template_key="youth_leader", group_id=group.pk))
        with self.assertRaisesMessage(CommandError, "bereits zu einer anderen Vorlage"):
            run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True, expected=token)

    def test_explicit_binding_can_create_missing_template_after_seed_name_collision(self):
        RoleTemplate.objects.filter(key="youth_leader").delete()
        group, role = self._legacy_group()
        comparison = run_reconcile(template_key="youth_leader", group_id=group.pk)
        self.assertIn("vorhanden=False", comparison)
        self.assertFalse(RoleTemplate.objects.filter(key="youth_leader").exists())
        run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True, expected=fingerprint(comparison))
        self.assertEqual(RoleTemplate.objects.get(key="youth_leader").group_id, group.pk)
        self.assertTrue(role.groups.filter(pk=group.pk).exists())

    def test_apply_requires_explicit_comparison_fingerprint(self):
        group, _ = self._legacy_group()
        with self.assertRaisesMessage(CommandError, "--apply verlangt"):
            run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True)

    def test_external_group_mapping_is_visible_and_part_of_fingerprint(self):
        group, _ = self._legacy_group()
        config = OIDCConfig.objects.create()
        mapping = OIDCGroupMapping.objects.create(
            oidc_config=config,
            group_claim_value="legacy-role",
            department=self.department,
        )
        mapping.auth_groups.add(group)
        audit = run_reconcile()
        self.assertIn(f"OIDC-Mapping-IDs=[{mapping.pk}]", audit)
        token = fingerprint(run_reconcile(template_key="youth_leader", group_id=group.pk))
        mapping.auth_groups.remove(group)
        with self.assertRaisesMessage(CommandError, "Zustand seit dem Vergleich geändert"):
            run_reconcile(template_key="youth_leader", group_id=group.pk, apply=True, expected=token)
