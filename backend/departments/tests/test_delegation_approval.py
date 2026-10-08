from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.delegation import approval_digest, delegation_approved
from departments.models import RoleTemplate
from departments.role_comparison import compare_role_template
from users.mfa_policy import mfa_required


class DelegationApprovalTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser(username="approval-admin", password="test-only")
        cls.role = RoleTemplate.objects.get(key="youth_leader")

    def approve(self):
        self.client.force_authenticate(self.admin)
        return self.client.post(
            f"/api/v1/admin/role-templates/{self.role.pk}/delegation/",
            {
                "fingerprint": compare_role_template(self.role)["fingerprint"],
                "approved": True,
            },
            format="json",
        )

    def test_seed_requires_explicit_approval_and_raw_permission_changes_invalidate_it(self):
        self.assertFalse(delegation_approved(self.role))
        self.assertEqual(self.approve().status_code, 200)
        self.role.refresh_from_db()
        self.assertTrue(delegation_approved(self.role))
        self.role.group.permissions.add(
            Permission.objects.get(content_type__app_label="members", codename="export_member")
        )
        self.assertFalse(delegation_approved(self.role))
        self.assertEqual(self.approve().status_code, 200)

    def test_approval_refuses_privileged_permissions(self):
        self.role.group.permissions.add(Permission.objects.get(content_type__app_label="auth", codename="change_group"))
        self.assertEqual(self.approve().status_code, 400)
        self.role.delegation_approval = approval_digest(self.role)
        self.assertFalse(delegation_approved(self.role))

    def test_anonymization_is_never_delegated_as_an_ordinary_subject_role(self):
        self.role.group.permissions.add(
            Permission.objects.get(content_type__app_label="inventory", codename="clear_former_member_names")
        )
        self.assertEqual(self.approve().status_code, 400)

    def test_settings_permission_alone_cannot_assign_external_roles(self):
        user = get_user_model().objects.create_user(username="integration-config-only")
        user.user_permissions.add(Permission.objects.get(codename="change_all_settings"))
        self.client.force_authenticate(user)
        for url in ("/api/v1/ldap-department-mappings/", "/api/v1/oidc-group-mappings/"):
            self.assertEqual(self.client.post(url, {}, format="json").status_code, 403)

    def test_approval_refuses_organization_and_archived_roles(self):
        self.role = RoleTemplate.objects.get(key="inventory_manager_organization")
        self.assertEqual(self.approve().status_code, 400)
        self.role = RoleTemplate.objects.get(key="youth_leader")
        self.role.is_archived = True
        self.role.save()
        self.assertEqual(self.approve().status_code, 400)

    def test_custom_delegation_permission_requires_mfa(self):
        user = get_user_model().objects.create_user(username="custom-delegator")
        user.user_permissions.add(Permission.objects.get(codename="can_delegate_roles"))
        self.assertTrue(mfa_required(user))

    def test_catalog_delivers_assignment_and_settings_rights_without_subject_rights(self):
        role = RoleTemplate.objects.get(key="system_administrator")
        names = set(role.group.permissions.values_list("content_type__app_label", "codename"))
        self.assertIn(("departments", "can_assign_roles"), names)
        self.assertIn(("settings_manager", "change_all_settings"), names)
        self.assertNotIn(("members", "view_member"), names)
