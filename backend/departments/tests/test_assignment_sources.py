from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.assignment_sources import set_local_groups
from departments.models import Department, RoleGrant, RoleTemplate, UserDepartmentRole
from settings_manager.models import LDAPConfig, LDAPDepartmentRoleMapping, OIDCConfig, OIDCGroupMapping
from users.ldap_backend import ConfigurableLDAPBackend
from users.oidc_backend import JFManagerOIDCBackend


class AssignmentSourceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.user = get_user_model().objects.create_user(username="source-target")
        cls.admin = get_user_model().objects.create_superuser(username="source-admin", password="test-only")
        cls.department = Department.objects.create(name="Source A", code="source-a")
        cls.supervisor = RoleTemplate.objects.get(key="supervisor")
        cls.planner = RoleTemplate.objects.get(key="training_planner")
        cls.ldap = LDAPConfig.get_or_create_default()
        cls.oidc = OIDCConfig.get_or_create_default()
        cls.ldap_mapping = LDAPDepartmentRoleMapping.objects.create(
            ldap_config=cls.ldap, ldap_group_dn="cn=source-test", department=cls.department, revoke_on_mismatch=True
        )
        cls.ldap_mapping.auth_groups.add(cls.supervisor.group)
        cls.oidc_mapping = OIDCGroupMapping.objects.create(
            oidc_config=cls.oidc, group_claim_value="source-test", department=cls.department, revoke_on_mismatch=True
        )
        cls.oidc_mapping.auth_groups.add(cls.supervisor.group)

    def oidc_sync(self, groups):
        JFManagerOIDCBackend()._sync_group_mappings(self.user, groups, self.oidc)

    def ldap_sync(self, groups):
        self.user.ldap_user = SimpleNamespace(group_dns=groups)
        with patch.object(ConfigurableLDAPBackend, "_active_config", return_value=self.ldap):
            ConfigurableLDAPBackend()._sync_department_roles(self.user)

    def group_ids(self):
        return set(
            UserDepartmentRole.objects.filter(user=self.user, department=self.department).values_list(
                "groups__pk", flat=True
            )
        ) - {None}

    def test_local_and_other_provider_survive_external_mismatch(self):
        set_local_groups(self.user, self.department.pk, [self.supervisor.group, self.planner.group])
        self.oidc_sync(["source-test"])
        self.ldap_sync(["cn=source-test"])
        self.assertEqual(RoleGrant.objects.filter(user=self.user, group=self.supervisor.group).count(), 3)
        self.oidc_sync([])
        self.assertEqual(self.group_ids(), {self.supervisor.group_id, self.planner.group_id})
        self.assertFalse(RoleGrant.objects.filter(source="oidc").exists())
        self.ldap_sync([])
        self.assertEqual(self.group_ids(), {self.supervisor.group_id, self.planner.group_id})

    def test_external_only_mismatch_removes_only_its_group(self):
        self.oidc_sync(["source-test"])
        set_local_groups(self.user, self.department.pk, [self.planner.group])
        self.oidc_sync([])
        self.assertEqual(self.group_ids(), {self.planner.group_id})

    def test_multiple_mappings_and_immediate_mapping_deletion_keep_other_sources(self):
        other = OIDCGroupMapping.objects.create(
            oidc_config=self.oidc, group_claim_value="another", department=self.department, revoke_on_mismatch=True
        )
        other.auth_groups.add(self.supervisor.group)
        self.oidc_sync(["source-test", "another"])
        self.oidc_mapping.delete()
        self.assertEqual(self.group_ids(), {self.supervisor.group_id})
        other.delete()
        self.assertEqual(self.group_ids(), set())

    def test_mapping_change_replaces_its_groups_on_verified_login(self):
        self.oidc_sync(["source-test"])
        self.oidc_mapping.auth_groups.set([self.planner.group])
        self.oidc_sync(["source-test"])
        self.assertEqual(self.group_ids(), {self.planner.group_id})

    def test_retain_on_mismatch_and_idempotent_sync(self):
        self.oidc_mapping.revoke_on_mismatch = False
        self.oidc_mapping.save()
        self.oidc_sync(["source-test"])
        self.oidc_sync(["source-test"])
        self.oidc_sync([])
        self.assertEqual(RoleGrant.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.group_ids(), {self.supervisor.group_id})

    def test_organization_oidc_role_and_local_source_are_independent(self):
        role = RoleTemplate.objects.get(key="inventory_manager_organization")
        mapping = OIDCGroupMapping.objects.create(
            oidc_config=self.oidc, group_claim_value="org-test", department=None, revoke_on_mismatch=True
        )
        mapping.auth_groups.add(role.group)
        set_local_groups(self.user, None, [role.group])
        self.oidc_sync(["org-test"])
        self.oidc_sync([])
        self.assertTrue(self.user.groups.filter(pk=role.group_id).exists())
        self.assertEqual(RoleGrant.objects.filter(user=self.user, department=None).count(), 1)

    def test_archived_role_keeps_existing_external_assignment_but_is_not_newly_assigned(self):
        self.oidc_sync(["source-test"])
        self.supervisor.is_archived = True
        self.supervisor.save()
        self.oidc_sync(["source-test"])
        self.assertEqual(self.group_ids(), {self.supervisor.group_id})
        self.oidc_sync([])
        self.oidc_sync(["source-test"])
        self.assertEqual(self.group_ids(), set())

    def test_old_unmarked_assignment_is_preserved_as_local_without_guessing_origin(self):
        UserDepartmentRole.objects.create(user=self.user, department=self.department).groups.add(self.supervisor.group)
        self.oidc_sync(["source-test"])
        self.oidc_sync([])
        self.assertEqual(self.group_ids(), {self.supervisor.group_id})
        self.assertTrue(RoleGrant.objects.filter(user=self.user, source="local").exists())

    def test_mapping_api_rejects_unbound_scope_mismatched_or_archived_groups(self):
        self.client.force_authenticate(self.admin)
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="Unbound")
        role = RoleTemplate.objects.get(key="inventory_manager_organization")
        for ids in ([group.pk], [role.group_id], []):
            response = self.client.post(
                "/api/v1/oidc-group-mappings/",
                {
                    "group_claim_value": "bad",
                    "department": self.department.pk,
                    "auth_group_ids": ids,
                },
                format="json",
            )
            self.assertEqual(response.status_code, 400)
        response = self.client.post(
            "/api/v1/oidc-group-mappings/",
            {
                "group_claim_value": "valid",
                "department": self.department.pk,
                "auth_group_ids": [self.supervisor.group_id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_legacy_admin_department_update_preserves_external_grant(self):
        self.oidc_sync(["source-test"])
        role = self.user.department_roles.get(department=self.department)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/v1/admin/department-roles/{role.pk}/", {"group_ids": [self.planner.group_id]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.group_ids(), {self.planner.group_id, self.supervisor.group_id})
        self.assertEqual(self.client.delete(f"/api/v1/admin/department-roles/{role.pk}/").status_code, 204)
        self.assertEqual(self.group_ids(), {self.supervisor.group_id})

    def test_legacy_global_update_preserves_external_grant_and_rejects_department_template(self):
        role = RoleTemplate.objects.get(key="inventory_manager_organization")
        mapping = OIDCGroupMapping.objects.create(oidc_config=self.oidc, group_claim_value="org", department=None)
        mapping.auth_groups.add(role.group)
        self.oidc_sync(["org"])
        self.client.force_authenticate(self.admin)
        url = f"/api/v1/admin/users/{self.user.pk}/set-groups/"
        self.assertEqual(self.client.patch(url, {"group_ids": []}, format="json").status_code, 200)
        self.assertTrue(self.user.groups.filter(pk=role.group_id).exists())
        self.assertEqual(
            self.client.patch(url, {"group_ids": [self.supervisor.group_id]}, format="json").status_code, 400
        )
