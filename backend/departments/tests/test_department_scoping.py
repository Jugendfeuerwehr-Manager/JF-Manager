"""
Department scoping permission tests.

Covers:
  - Unauthenticated users are denied access
  - Org-wide users (is_staff / can_access_all_departments) see all data
  - Department-scoped users only see data belonging to their departments
  - Transitive parent scoping via children's department memberships
  - The ?department= query param is validated for dept-scoped users
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(username, *, is_staff=False):
    return User.objects.create_user(username=username, password="pw", is_staff=is_staff)


def _assign_dept(user, department):
    """Create a UserDepartmentRole (no groups needed for scoping tests)."""
    return UserDepartmentRole.objects.create(user=user, department=department)


def _make_member(name, departments=None):
    m = Member.objects.create(name=name, lastname="Test")
    if departments:
        m.departments.set(departments)
    return m


def _make_parent(name, children=None):
    p = Parent.objects.create(name=name, lastname="Test")
    if children:
        p.children.set(children)
    return p


# ---------------------------------------------------------------------------
# Base fixture
# ---------------------------------------------------------------------------


class DeptScopingFixture(APITestCase):
    """
    Two departments (Dept A, Dept B), three users:
      - staff_user   : is_staff=True (org-wide)
      - user_a       : scoped to Dept A only
      - user_b       : scoped to Dept B only
    """

    @classmethod
    def setUpTestData(cls):
        cls.dept_a = Department.objects.create(name="Abteilung A", code="dept-a")
        cls.dept_b = Department.objects.create(name="Abteilung B", code="dept-b")

        cls.staff_user = _make_user("staff", is_staff=True)
        cls.user_a = _make_user("user_a")
        cls.user_b = _make_user("user_b")

        _assign_dept(cls.user_a, cls.dept_a)
        _assign_dept(cls.user_b, cls.dept_b)


# ---------------------------------------------------------------------------
# 1. Members endpoint
# ---------------------------------------------------------------------------


class MemberScopingTest(DeptScopingFixture):
    """GET /api/v1/members/ — DepartmentScopeViewSetMixin with department_field='departments'."""

    URL = "/api/v1/members/"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.member_a = _make_member("Alice", departments=[cls.dept_a])
        cls.member_b = _make_member("Bob", departments=[cls.dept_b])
        cls.member_both = _make_member("Charlie", departments=[cls.dept_a, cls.dept_b])
        cls.member_none = _make_member("Dave")  # no department (central record)

    def _ids(self, response):
        return {item["id"] for item in response.data["results"]}

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_sees_all_members(self):
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.member_a.id, ids)
        self.assertIn(self.member_b.id, ids)
        self.assertIn(self.member_both.id, ids)
        self.assertIn(self.member_none.id, ids)

    def test_user_a_sees_only_dept_a_members(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.member_a.id, ids)
        self.assertIn(self.member_both.id, ids)  # in both depts — still visible to A
        self.assertNotIn(self.member_none.id, ids)  # no dept → NOT visible (include_central_records=False)
        self.assertNotIn(self.member_b.id, ids)

    def test_user_b_sees_only_dept_b_members(self):
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.member_b.id, ids)
        self.assertIn(self.member_both.id, ids)
        self.assertNotIn(self.member_a.id, ids)

    def test_staff_can_filter_by_department(self):
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get(self.URL, {"department": self.dept_a.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.member_a.id, ids)
        self.assertIn(self.member_both.id, ids)
        self.assertNotIn(self.member_b.id, ids)

    def test_user_a_cannot_filter_by_dept_b(self):
        """Dept-scoped user requesting another dept must be denied."""
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(self.URL, {"department": self.dept_b.id})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_a_can_filter_by_own_dept(self):
        """Dept-scoped user requesting their own dept is allowed."""
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(self.URL, {"department": self.dept_a.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.member_a.id, ids)
        self.assertNotIn(self.member_b.id, ids)


# ---------------------------------------------------------------------------
# 2. Parents endpoint — transitive scoping
# ---------------------------------------------------------------------------


class ParentScopingTest(DeptScopingFixture):
    """GET /api/v1/parents/ — custom transitive scoping via children's depts."""

    URL = "/api/v1/parents/"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.member_a = _make_member("Alice", departments=[cls.dept_a])
        cls.member_b = _make_member("Bob", departments=[cls.dept_b])
        cls.member_both = _make_member("Charlie", departments=[cls.dept_a, cls.dept_b])

        # Parent with child in A only
        cls.parent_a = _make_parent("ParentA", children=[cls.member_a])
        # Parent with child in B only
        cls.parent_b = _make_parent("ParentB", children=[cls.member_b])
        # Parent with child in both
        cls.parent_both = _make_parent("ParentBoth", children=[cls.member_both])
        # Parent with no children (just created, not yet linked)
        cls.parent_orphan = _make_parent("ParentOrphan")

    def _ids(self, response):
        return {item["id"] for item in response.data["results"]}

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_sees_all_parents(self):
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.parent_a.id, ids)
        self.assertIn(self.parent_b.id, ids)
        self.assertIn(self.parent_both.id, ids)
        self.assertIn(self.parent_orphan.id, ids)

    def test_user_a_sees_parents_of_dept_a_children(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.parent_a.id, ids)
        self.assertIn(self.parent_both.id, ids)  # child is in dept A too
        self.assertIn(self.parent_orphan.id, ids)  # no children — still visible
        self.assertNotIn(self.parent_b.id, ids)  # child is only in dept B

    def test_user_b_sees_parents_of_dept_b_children(self):
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.parent_b.id, ids)
        self.assertIn(self.parent_both.id, ids)
        self.assertNotIn(self.parent_a.id, ids)

    def test_staff_can_filter_parents_by_department(self):
        """Org-wide user can narrow to dept A — should only show parents with children in A."""
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get(self.URL, {"department": self.dept_a.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.parent_a.id, ids)
        self.assertIn(self.parent_both.id, ids)
        self.assertNotIn(self.parent_b.id, ids)
        # Orphan parents have no children in any dept, so they do NOT match the filter
        self.assertNotIn(self.parent_orphan.id, ids)

    def test_user_a_cannot_filter_by_dept_b(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(self.URL, {"department": self.dept_b.id})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_department_param_returns_400(self):
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get(self.URL, {"department": "notanumber"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# 3. Departments endpoint
# ---------------------------------------------------------------------------


class DepartmentEndpointTest(DeptScopingFixture):
    """GET /api/v1/departments/ — staff sees all, scoped sees own."""

    URL = "/api/v1/departments/"

    def _ids(self, response):
        return {item["id"] for item in response.data["results"]}

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_sees_all_departments(self):
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.dept_a.id, ids)
        self.assertIn(self.dept_b.id, ids)

    def test_dept_a_user_sees_own_department(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.dept_a.id, ids)
        self.assertNotIn(self.dept_b.id, ids)


# ---------------------------------------------------------------------------
# 4. Admin: UserDepartmentRole endpoint
# ---------------------------------------------------------------------------


class UserDepartmentRoleAdminTest(DeptScopingFixture):
    """GET /api/v1/admin/department-roles/ — staff only."""

    URL = "/api/v1/admin/department-roles/"

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_denied(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(self.URL)
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED))

    def test_staff_can_list_roles(self):
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Both roles from setUpTestData should be present
        ids = {item["id"] for item in resp.data["results"]}
        self.assertGreaterEqual(len(ids), 2)

    def test_staff_can_create_role(self):
        new_user = _make_user("new_user_for_role")
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.post(
            self.URL, {"user": new_user.id, "department": self.dept_a.id, "group_ids": []}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["department"]["id"], self.dept_a.id)


# ---------------------------------------------------------------------------
# 5. can_access_all_departments permission (non-staff org-wide user)
# ---------------------------------------------------------------------------


class OrgWidePermissionTest(DeptScopingFixture):
    """A non-staff user with departments.can_access_all_departments sees all data."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.member_a = _make_member("Alice", departments=[cls.dept_a])
        cls.member_b = _make_member("Bob", departments=[cls.dept_b])

        cls.perm_user = _make_user("perm_user", is_staff=False)
        perm = Permission.objects.get(codename="can_access_all_departments")
        cls.perm_user.user_permissions.add(perm)

    def _ids(self, response):
        return {item["id"] for item in response.data["results"]}

    def test_perm_user_sees_all_members(self):
        # Re-fetch to ensure permission cache is fresh
        user = User.objects.get(pk=self.perm_user.pk)
        self.client.force_authenticate(user=user)
        resp = self.client.get("/api/v1/members/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(self.member_a.id, ids)
        self.assertIn(self.member_b.id, ids)

    def test_perm_user_sees_all_parents(self):
        parent_a = _make_parent("PA", children=[self.member_a])
        parent_b = _make_parent("PB", children=[self.member_b])
        user = User.objects.get(pk=self.perm_user.pk)
        self.client.force_authenticate(user=user)
        resp = self.client.get("/api/v1/parents/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = self._ids(resp)
        self.assertIn(parent_a.id, ids)
        self.assertIn(parent_b.id, ids)
