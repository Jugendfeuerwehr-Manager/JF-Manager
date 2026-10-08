from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from rest_framework.test import APITestCase

from departments.delegation import approval_digest
from departments.models import Department, RoleGrant, RoleTemplate, UserDepartmentRole


class RoleAssignmentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        User = get_user_model()
        cls.admin = User.objects.create_superuser(username="assign-admin", password="test-only")
        cls.director = User.objects.create_user(username="assign-director")
        cls.leader = User.objects.create_user(username="assign-dept-director")
        cls.person = User.objects.create_user(username="assign-target")
        cls.other = User.objects.create_user(username="assign-other")
        cls.department = Department.objects.create(name="A", code="assign-a")
        cls.foreign = Department.objects.create(name="B", code="assign-b")
        cls.director.groups.add(RoleTemplate.objects.get(key="youth_director").group)
        UserDepartmentRole.objects.create(user=cls.leader, department=cls.department).groups.add(
            RoleTemplate.objects.get(key="department_youth_director").group
        )
        cls.role = RoleTemplate.objects.get(key="supervisor")
        cls.role.delegation_approval = approval_digest(cls.role)
        cls.role.save()

    def setUp(self):
        self.client.force_authenticate(self.leader)
        self.data = {
            "user_id": self.person.pk,
            "department_id": self.department.pk,
            "template_id": self.role.pk,
            "operation": "add",
        }

    def preview(self, **changes):
        return self.client.post("/api/v1/role-assignments/preview/", {**self.data, **changes}, format="json")

    def apply(self, fingerprint, **changes):
        return self.client.post(
            "/api/v1/role-assignments/apply/", {**self.data, **changes, "fingerprint": fingerprint}, format="json"
        )

    def test_scoped_leader_assigns_approved_role_and_explains_source(self):
        preview = self.preview()
        self.assertEqual(preview.status_code, 200)
        self.assertIn("servicebook.change_attendance", preview.data["added_permissions"])
        response = self.apply(preview.data["fingerprint"])
        self.assertEqual(response.status_code, 200)
        role = self.person.department_roles.get(department=self.department)
        self.assertEqual(list(role.groups.all()), [self.role.group])
        self.assertEqual(response.data["roles"][0]["sources"], [{"source": "local", "source_key": ""}])
        self.assertEqual(self.apply(self.preview().data["fingerprint"]).status_code, 200)
        self.assertEqual(RoleGrant.objects.filter(user=self.person).count(), 1)

    def test_foreign_department_is_denied_even_with_manipulated_filter(self):
        self.assertEqual(self.preview(department_id=self.foreign.pk).status_code, 403)
        response = self.client.post(
            f"/api/v1/role-assignments/apply/?department={self.department.pk}",
            {**self.data, "department_id": self.foreign.pk, "fingerprint": "anything"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.person.department_roles.exists())

    def test_self_assignment_and_privileged_target_are_denied(self):
        self.assertEqual(self.preview(user_id=self.leader.pk).status_code, 403)
        self.assertEqual(self.preview(user_id=self.admin.pk).status_code, 403)
        self.assertEqual(self.preview(user_id=self.director.pk).status_code, 403)

    def test_organization_roles_only_for_system_administration(self):
        role = RoleTemplate.objects.get(key="inventory_manager_organization")
        self.assertEqual(self.preview(template_id=role.pk, department_id=None).status_code, 403)
        self.client.force_authenticate(self.director)
        self.assertEqual(self.preview(template_id=role.pk, department_id=None).status_code, 403)
        self.client.force_authenticate(self.admin)
        preview = self.preview(template_id=role.pk, department_id=None)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(
            self.apply(preview.data["fingerprint"], template_id=role.pk, department_id=None).status_code, 200
        )
        self.assertTrue(self.person.groups.filter(pk=role.group_id).exists())

    def test_department_leadership_only_for_organization_director(self):
        role = RoleTemplate.objects.get(key="department_youth_director")
        self.assertEqual(self.preview(template_id=role.pk).status_code, 403)
        self.client.force_authenticate(self.director)
        preview = self.preview(template_id=role.pk, department_id=self.foreign.pk)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(
            self.apply(preview.data["fingerprint"], template_id=role.pk, department_id=self.foreign.pk).status_code, 200
        )

    def test_unapproved_archived_and_changed_templates_are_denied(self):
        other = RoleTemplate.objects.get(key="youth_leader")
        self.assertEqual(self.preview(template_id=other.pk).status_code, 403)
        self.role.is_archived = True
        self.role.save()
        self.assertEqual(self.preview().status_code, 403)
        self.role.is_archived = False
        self.role.save()
        self.role.group.permissions.add(Permission.objects.get(codename="export_member"))
        self.assertEqual(self.preview().status_code, 403)

    def test_stale_preview_does_not_change_assignments(self):
        preview = self.preview()
        self.client.force_authenticate(self.admin)
        RoleGrant.objects.create(
            user=self.person,
            group=self.role.group,
            department=self.department,
            source="oidc",
            source_key="test-mapping",
        )
        self.assertEqual(self.apply(preview.data["fingerprint"]).status_code, 409)
        self.assertFalse(RoleGrant.objects.filter(user=self.person, source="local").exists())

    def test_preview_is_bound_to_person_operation_and_scope(self):
        self.client.force_authenticate(self.admin)
        fingerprint = self.preview().data["fingerprint"]
        for changes in ({"user_id": self.other.pk}, {"operation": "remove"}, {"department_id": self.foreign.pk}):
            self.assertEqual(self.apply(fingerprint, **changes).status_code, 409)
        self.assertFalse(RoleGrant.objects.filter(source="local").exists())

    def test_external_assignment_survives_local_removal(self):
        self.client.force_authenticate(self.admin)
        role = UserDepartmentRole.objects.create(user=self.person, department=self.department)
        role.groups.add(self.role.group)
        RoleGrant.objects.create(
            user=self.person,
            group=self.role.group,
            department=self.department,
            source="oidc",
            source_key="test-mapping",
        )
        self.assertEqual(self.apply(self.preview().data["fingerprint"]).status_code, 200)
        preview = self.preview(operation="remove")
        self.assertTrue(preview.data["retained_external"])
        self.assertEqual(preview.data["removed_permissions"], [])
        self.assertEqual(self.apply(preview.data["fingerprint"], operation="remove").status_code, 200)
        self.assertTrue(role.groups.filter(pk=self.role.group_id).exists())
        self.assertFalse(RoleGrant.objects.filter(source="local", user=self.person).exists())

    def test_staff_and_scope_without_assignment_right_have_no_options(self):
        self.other.is_staff = True
        self.other.save()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/role-assignments/options/").status_code, 403)
        self.assertEqual(self.preview().status_code, 403)

    def test_scope_mismatch_inactive_person_and_unknown_fields(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.preview(department_id=None).status_code, 403)
        self.other.is_active = False
        self.other.save()
        self.assertEqual(self.preview(user_id=self.other.pk).status_code, 403)
        self.assertEqual(self.preview(is_superuser=True).status_code, 400)

    def test_explanation_hides_other_departments_and_global_roles_from_delegate(self):
        self.person.groups.add(RoleTemplate.objects.get(key="inventory_manager_organization").group)
        for department in (self.department, self.foreign):
            UserDepartmentRole.objects.create(user=self.person, department=department).groups.add(self.role.group)
        response = self.client.get("/api/v1/role-assignments/explain/", {"user": self.person.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["department_id"] for row in response.data["roles"]], [self.department.pk])
        self.client.force_authenticate(self.person)
        response = self.client.get("/api/v1/role-assignments/explain/")
        self.assertEqual(len(response.data["roles"]), 3)
        self.assertEqual(self.client.get("/api/v1/role-assignments/explain/", {"user": self.other.pk}).status_code, 403)

    def test_options_include_only_approved_and_permitted_roles(self):
        response = self.client.get("/api/v1/role-assignments/options/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["organization_allowed"])
        self.assertEqual(response.data["departments"], [{"id": self.department.pk, "name": "A"}])
        self.assertEqual([row["id"] for row in response.data["roles"]], [self.role.pk])

    def test_real_session_requires_step_up_before_preview(self):
        self.client.force_authenticate(None)
        self.client.force_login(self.admin)
        from users.mfa import MFA_VERIFIED_KEY

        session = self.client.session
        session["_reauthenticated_at"] = 0
        session[MFA_VERIFIED_KEY] = 1
        session.save()
        response = self.preview()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(str(response.data["code"]), "reauthentication_required")

    def test_system_administrator_without_staff_manages_identities(self):
        from django.contrib.auth import get_user_model

        system = get_user_model().objects.create_user(username="system-without-staff")
        system.groups.add(RoleTemplate.objects.get(key="system_administrator").group)
        self.client.force_authenticate(system)
        self.assertEqual(self.client.get("/api/v1/admin/users/").status_code, 200)
        response = self.client.patch(f"/api/v1/admin/users/{self.person.pk}/", {"first_name": "Test"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/users/{self.admin.pk}/", {"first_name": "Bad"}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/users/{self.person.pk}/", {"is_superuser": True}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/groups/{RoleTemplate.objects.get(key='system_administrator').group_id}/",
                {"name": "Own"},
                format="json",
            ).status_code,
            403,
        )

    def test_department_identity_permission_does_not_grant_global_identity_access(self):
        group = self.role.group
        group.permissions.add(Permission.objects.get(content_type__app_label="users", codename="view_customuser"))
        UserDepartmentRole.objects.create(user=self.other, department=self.department).groups.add(group)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/admin/users/").status_code, 403)
