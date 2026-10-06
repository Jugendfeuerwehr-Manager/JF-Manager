"""Organizations without departments keep creating lists (organization-wide lists)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member, MemberList, MemberListEntry

LIST_RIGHTS = ["view_memberlist", "add_memberlist", "change_memberlist", "delete_memberlist"]


def _group(name, codenames, org_wide=False):
    group = Group.objects.create(name=name)
    group.permissions.add(*Permission.objects.filter(content_type__app_label="members", codename__in=codenames))
    if org_wide:
        group.permissions.add(Permission.objects.get(codename="can_access_all_departments"))
    return group


class OrganizationWideListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.org_editor = users.create_user(username="org-list-editor", password="test-only-password")
        cls.org_editor.groups.add(_group("Org list editor", LIST_RIGHTS, org_wide=True))
        cls.global_without_scope = users.create_user(username="org-list-no-scope", password="test-only-password")
        cls.global_without_scope.groups.add(_group("Global list rights without scope", LIST_RIGHTS))
        cls.member = Member.objects.create(name="Org", lastname="Member")

    def setUp(self):
        self.client.force_authenticate(user=self.org_editor)

    def test_org_wide_user_creates_list_without_department_and_manages_entries(self):
        created = self.client.post("/api/v1/member-lists/", {"name": "Ausflug", "department": None}, format="json")

        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertTrue(created.data["organization_wide"])
        member_list = MemberList.objects.get(pk=created.data["id"])
        self.assertIsNone(member_list.department_id)
        self.assertTrue(member_list.organization_wide)

        added = self.client.post(
            f"/api/v1/member-lists/{member_list.pk}/add_member/", {"member_id": self.member.pk}, format="json"
        )
        self.assertEqual(added.status_code, status.HTTP_201_CREATED)
        renamed = self.client.patch(f"/api/v1/member-lists/{member_list.pk}/", {"name": "Zeltlager"}, format="json")
        self.assertEqual(renamed.status_code, status.HTTP_200_OK)
        listed = self.client.get("/api/v1/member-lists/")
        self.assertIn(member_list.pk, [item["id"] for item in listed.data["results"]])
        deleted = self.client.delete(f"/api/v1/member-lists/{member_list.pk}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_event_import_without_department_uses_all_members(self):
        response = self.client.post(
            "/api/v1/member-lists/create_from_event_type/",
            {"name": "Alle", "department": None, "invert": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        member_list = MemberList.objects.get(pk=response.data["id"])
        self.assertTrue(member_list.organization_wide)
        self.assertTrue(MemberListEntry.objects.filter(member_list=member_list, member=self.member).exists())

    def test_global_rights_without_org_scope_cannot_create_or_see_org_lists(self):
        existing = MemberList.objects.create(name="Org", organization_wide=True)
        self.client.force_authenticate(user=self.global_without_scope)

        created = self.client.post("/api/v1/member-lists/", {"name": "Nein", "department": None}, format="json")
        listed = self.client.get("/api/v1/member-lists/")
        detail = self.client.get(f"/api/v1/member-lists/{existing.pk}/")

        self.assertEqual(created.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn(existing.pk, [item["id"] for item in listed.data["results"]])
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_department_role_cannot_create_org_list(self):
        department = Department.objects.create(name="Inactive role dept", code="inactive-role-dept", is_active=False)
        user = get_user_model().objects.create_user(username="org-list-role", password="test-only-password")
        UserDepartmentRole.objects.create(user=user, department=department).groups.add(
            _group("Role list editor", LIST_RIGHTS)
        )
        self.client.force_authenticate(user=user)

        response = self.client.post("/api/v1/member-lists/", {"name": "Nein", "department": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(MemberList.objects.filter(name="Nein").exists())

    def test_list_without_department_is_rejected_once_an_active_department_exists(self):
        Department.objects.create(name="Erste Abteilung", code="erste-abteilung")

        response = self.client.post("/api/v1/member-lists/", {"name": "Nein", "department": None}, format="json")
        imported = self.client.post(
            "/api/v1/member-lists/create_from_event_type/",
            {"name": "Nein", "department": None, "invert": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department", response.data)
        self.assertEqual(imported.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(MemberList.objects.filter(name="Nein").exists())

    def test_existing_org_list_keeps_working_after_departments_are_added_but_cannot_move(self):
        member_list = MemberList.objects.create(name="Org", organization_wide=True)
        department = Department.objects.create(name="Spätere Abteilung", code="spaetere-abteilung")

        moved = self.client.patch(
            f"/api/v1/member-lists/{member_list.pk}/", {"department": department.pk}, format="json"
        )
        added = self.client.post(
            f"/api/v1/member-lists/{member_list.pk}/add_member/", {"member_id": self.member.pk}, format="json"
        )

        self.assertEqual(moved.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(added.status_code, status.HTTP_201_CREATED)

    def test_org_lists_stay_out_of_the_legacy_queue(self):
        org_list = MemberList.objects.create(name="Org", organization_wide=True)
        legacy = MemberList.objects.create(name="Alt")
        superuser = get_user_model().objects.create_superuser(username="org-list-admin", password="test-only-password")
        self.client.force_authenticate(user=superuser)

        pending = self.client.get("/api/v1/member-lists/pending-resolution/")
        resolve = self.client.get(f"/api/v1/member-lists/{org_list.pk}/resolve-legacy/")

        self.assertEqual([item["id"] for item in pending.data], [legacy.pk])
        self.assertEqual(resolve.status_code, status.HTTP_404_NOT_FOUND)

    def test_unresolved_legacy_list_stays_hidden_from_org_wide_user(self):
        legacy = MemberList.objects.create(name="Alt")

        listed = self.client.get("/api/v1/member-lists/")

        self.assertNotIn(legacy.pk, [item["id"] for item in listed.data["results"]])
