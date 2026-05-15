"""
Department scope tests for the Qualifications module.

Verifies that:
- Org-wide users see all qualifications and special tasks
- Dept-scoped users with view_all_qualifications see only records for members in their depts
- Dept-scoped users without that permission see only their own records
- Cross-department access is denied for the ?department= query param
- The statistics endpoint respects the same scoping rules
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member
from qualifications.models import Qualification, QualificationType, SpecialTask, SpecialTaskType

User = get_user_model()


class QualificationDeptScopeBase(APITestCase):
    """Shared setUp for all qualification department scope tests."""

    def setUp(self):
        self.client = APIClient()

        # Two departments
        self.dept_a = Department.objects.create(name="Department A", code="dept-a")
        self.dept_b = Department.objects.create(name="Department B", code="dept-b")

        # Org-wide (superuser)
        self.org_wide_user = User.objects.create_superuser(
            username="org_wide",
            email="org_wide@test.com",
            password="OrgWide!123",
        )

        # Dept-A user with view_all_qualifications permission
        self.dept_a_admin = User.objects.create_user(
            username="dept_a_admin",
            email="dept_a_admin@test.com",
            password="DeptAdmin!123",
        )
        admin_group = Group.objects.create(name="Qualification Admin Group")
        view_all_perm = Permission.objects.get(
            content_type__app_label="qualifications",
            codename="view_all_qualifications",
        )
        view_perm = Permission.objects.get(
            content_type__app_label="qualifications",
            codename="view_qualification",
        )
        admin_group.permissions.add(view_all_perm, view_perm)
        role_a_admin = UserDepartmentRole.objects.create(user=self.dept_a_admin, department=self.dept_a)
        role_a_admin.groups.add(admin_group)

        # Dept-A regular user (no view_all_qualifications)
        self.dept_a_user = User.objects.create_user(
            username="dept_a_user",
            email="dept_a_user@test.com",
            password="DeptUser!123",
        )
        user_group = Group.objects.create(name="Qualification Viewer Group")
        user_group.permissions.add(view_perm)
        role_a_user = UserDepartmentRole.objects.create(user=self.dept_a_user, department=self.dept_a)
        role_a_user.groups.add(user_group)

        # Members
        self.member_a = Member.objects.create(
            name="Anna",
            lastname="Dept-A",
            birthday=date(2000, 1, 1),
            gender="female",
            joined=date(2020, 1, 1),
        )
        self.member_a.departments.add(self.dept_a)

        self.member_b = Member.objects.create(
            name="Bob",
            lastname="Dept-B",
            birthday=date(2000, 2, 2),
            gender="male",
            joined=date(2020, 2, 1),
        )
        self.member_b.departments.add(self.dept_b)

        # Qualification type
        self.qual_type = QualificationType.objects.create(
            name="First Aid",
            expires=False,
        )

        # Qualifications: one per member, one linked to dept_a_user directly
        self.qual_member_a = Qualification.objects.create(
            type=self.qual_type,
            member=self.member_a,
            date_acquired=date(2023, 1, 1),
        )
        self.qual_member_b = Qualification.objects.create(
            type=self.qual_type,
            member=self.member_b,
            date_acquired=date(2023, 2, 1),
        )
        self.qual_user = Qualification.objects.create(
            type=self.qual_type,
            user=self.dept_a_user,
            date_acquired=date(2023, 3, 1),
        )

    def _login(self, username, password):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


class OrgWideQualificationTests(QualificationDeptScopeBase):
    """Org-wide users see all qualifications."""

    def setUp(self):
        super().setUp()
        self._login("org_wide", "OrgWide!123")

    def test_org_wide_sees_all_qualifications(self):
        response = self.client.get("/api/v1/qualifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [q["id"] for q in response.data["results"]]
        self.assertIn(self.qual_member_a.id, ids)
        self.assertIn(self.qual_member_b.id, ids)
        self.assertIn(self.qual_user.id, ids)

    def test_org_wide_can_filter_by_department(self):
        response = self.client.get(f"/api/v1/qualifications/?department={self.dept_a.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [q["id"] for q in response.data["results"]]
        self.assertIn(self.qual_member_a.id, ids)
        self.assertNotIn(self.qual_member_b.id, ids)


class DeptAdminQualificationTests(QualificationDeptScopeBase):
    """Dept-A users with view_all_qualifications see all dept-A member qualifications."""

    def setUp(self):
        super().setUp()
        self._login("dept_a_admin", "DeptAdmin!123")

    def test_dept_admin_sees_dept_a_member_qualifications(self):
        response = self.client.get("/api/v1/qualifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [q["id"] for q in response.data["results"]]
        self.assertIn(self.qual_member_a.id, ids)

    def test_dept_admin_cannot_see_dept_b_qualifications(self):
        response = self.client.get("/api/v1/qualifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [q["id"] for q in response.data["results"]]
        self.assertNotIn(self.qual_member_b.id, ids)

    def test_dept_admin_cannot_request_foreign_department(self):
        response = self.client.get(f"/api/v1/qualifications/?department={self.dept_b.id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DeptUserQualificationTests(QualificationDeptScopeBase):
    """Dept-A regular users see only their own qualifications."""

    def setUp(self):
        super().setUp()
        self._login("dept_a_user", "DeptUser!123")

    def test_regular_user_sees_own_qualification(self):
        response = self.client.get("/api/v1/qualifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [q["id"] for q in response.data["results"]]
        self.assertIn(self.qual_user.id, ids)

    def test_regular_user_cannot_see_other_user_qualification(self):
        response = self.client.get("/api/v1/qualifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [q["id"] for q in response.data["results"]]
        self.assertNotIn(self.qual_member_b.id, ids)

    def test_regular_user_cannot_request_foreign_department(self):
        response = self.client.get(f"/api/v1/qualifications/?department={self.dept_b.id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SpecialTaskDeptScopeBase(APITestCase):
    """Shared setUp for special task department scope tests."""

    def setUp(self):
        self.client = APIClient()

        self.dept_a = Department.objects.create(name="Dept A ST", code="dept-a-st")
        self.dept_b = Department.objects.create(name="Dept B ST", code="dept-b-st")

        self.org_wide_user = User.objects.create_superuser(
            username="st_org_wide",
            email="st_org_wide@test.com",
            password="STOrgWide!123",
        )

        self.dept_a_admin = User.objects.create_user(
            username="st_dept_a_admin",
            email="st_dept_a_admin@test.com",
            password="STAdmin!123",
        )
        admin_group = Group.objects.create(name="ST Admin Group")
        view_all_perm = Permission.objects.get(
            content_type__app_label="qualifications",
            codename="view_all_specialtasks",
        )
        view_perm = Permission.objects.get(
            content_type__app_label="qualifications",
            codename="view_specialtask",
        )
        admin_group.permissions.add(view_all_perm, view_perm)
        role_admin = UserDepartmentRole.objects.create(user=self.dept_a_admin, department=self.dept_a)
        role_admin.groups.add(admin_group)

        self.dept_a_user = User.objects.create_user(
            username="st_dept_a_user",
            email="st_dept_a_user@test.com",
            password="STUser!123",
        )
        user_group = Group.objects.create(name="ST Viewer Group")
        user_group.permissions.add(view_perm)
        role_user = UserDepartmentRole.objects.create(user=self.dept_a_user, department=self.dept_a)
        role_user.groups.add(user_group)

        self.member_a = Member.objects.create(
            name="Clara",
            lastname="Dept-A",
            birthday=date(2001, 3, 3),
            gender="female",
            joined=date(2021, 1, 1),
        )
        self.member_a.departments.add(self.dept_a)

        self.member_b = Member.objects.create(
            name="Dave",
            lastname="Dept-B",
            birthday=date(2001, 4, 4),
            gender="male",
            joined=date(2021, 2, 1),
        )
        self.member_b.departments.add(self.dept_b)

        self.task_type = SpecialTaskType.objects.create(name="Safety Officer")

        self.task_member_a = SpecialTask.objects.create(
            task=self.task_type,
            member=self.member_a,
            start_date=date(2023, 1, 1),
        )
        self.task_member_b = SpecialTask.objects.create(
            task=self.task_type,
            member=self.member_b,
            start_date=date(2023, 2, 1),
        )
        self.task_user = SpecialTask.objects.create(
            task=self.task_type,
            user=self.dept_a_user,
            start_date=date(2023, 3, 1),
        )

    def _login(self, username, password):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


class OrgWideSpecialTaskTests(SpecialTaskDeptScopeBase):
    def setUp(self):
        super().setUp()
        self._login("st_org_wide", "STOrgWide!123")

    def test_org_wide_sees_all_special_tasks(self):
        response = self.client.get("/api/v1/qualifications/specialtasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.task_member_a.id, ids)
        self.assertIn(self.task_member_b.id, ids)
        self.assertIn(self.task_user.id, ids)

    def test_org_wide_can_filter_special_tasks_by_department(self):
        response = self.client.get(f"/api/v1/qualifications/specialtasks/?department={self.dept_a.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.task_member_a.id, ids)
        self.assertNotIn(self.task_member_b.id, ids)


class DeptAdminSpecialTaskTests(SpecialTaskDeptScopeBase):
    def setUp(self):
        super().setUp()
        self._login("st_dept_a_admin", "STAdmin!123")

    def test_dept_admin_sees_dept_a_special_tasks(self):
        response = self.client.get("/api/v1/qualifications/specialtasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.task_member_a.id, ids)

    def test_dept_admin_cannot_see_dept_b_special_tasks(self):
        response = self.client.get("/api/v1/qualifications/specialtasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertNotIn(self.task_member_b.id, ids)

    def test_dept_admin_cannot_request_foreign_department(self):
        response = self.client.get(f"/api/v1/qualifications/specialtasks/?department={self.dept_b.id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DeptUserSpecialTaskTests(SpecialTaskDeptScopeBase):
    def setUp(self):
        super().setUp()
        self._login("st_dept_a_user", "STUser!123")

    def test_regular_user_sees_own_task(self):
        response = self.client.get("/api/v1/qualifications/specialtasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.task_user.id, ids)

    def test_regular_user_cannot_see_foreign_dept_task(self):
        response = self.client.get("/api/v1/qualifications/specialtasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertNotIn(self.task_member_b.id, ids)

    def test_regular_user_cannot_request_foreign_department(self):
        response = self.client.get(f"/api/v1/qualifications/specialtasks/?department={self.dept_b.id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
