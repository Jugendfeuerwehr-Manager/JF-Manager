from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from departments.models import Department, UserDepartmentRole

User = get_user_model()


class DepartmentScopeSecurityTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.allowed_department = Department.objects.create(name="Allowed Department", code="allowed")
        self.foreign_department = Department.objects.create(name="Foreign Department", code="foreign")

        self.user = User.objects.create_user(
            username="dept_user",
            email="dept_user@test.com",
            password="dept-user-password-123!",
        )

        role_group = Group.objects.create(name="Dept Members Viewer")
        view_member_permission = Permission.objects.get(
            content_type__app_label="members",
            codename="view_member",
        )
        role_group.permissions.add(view_member_permission)

        role = UserDepartmentRole.objects.create(user=self.user, department=self.allowed_department)
        role.groups.add(role_group)

        token_response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "dept_user", "password": "dept-user-password-123!"},
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

    def test_department_scoped_token_cannot_request_foreign_department(self):
        allowed_response = self.client.get(f"/api/v1/members/?department={self.allowed_department.id}")
        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)

        forbidden_response = self.client.get(f"/api/v1/members/?department={self.foreign_department.id}")
        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)
