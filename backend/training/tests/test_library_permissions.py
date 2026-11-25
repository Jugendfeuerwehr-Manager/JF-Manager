"""The library right from a department role allows contributing to the shared library."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, RoleTemplate, UserDepartmentRole
from training.models import LibraryBlock

User = get_user_model()
URL = "/api/v1/training/library/"


class LibraryPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.dept = Department.objects.create(name="A", code="a")
        cls.other = Department.objects.create(name="B", code="b")
        library_group = AuthGroup.objects.create(name="Abteilungsjugendwart mit Bibliothek")
        library_group.permissions.add(Permission.objects.get(codename="can_manage_library"))
        cls.department_editor = User.objects.create_user("ajw-a")
        UserDepartmentRole.objects.create(user=cls.department_editor, department=cls.dept).groups.add(library_group)
        cls.foreign_editor = User.objects.create_user("ajw-b")
        UserDepartmentRole.objects.create(user=cls.foreign_editor, department=cls.other).groups.add(library_group)
        planner_group = RoleTemplate.objects.get(key="training_planner").group
        cls.planner = User.objects.create_user("planer")
        UserDepartmentRole.objects.create(user=cls.planner, department=cls.dept).groups.add(planner_group)
        cls.global_editor = User.objects.create_user("redaktion")
        cls.global_editor.groups.add(RoleTemplate.objects.get(key="library_editor").group)

    def client_for(self, user=None):
        client = APIClient()
        if user:
            client.force_login(user)
        return client

    def create(self, user, title="Knoten"):
        return self.client_for(user).post(URL, {"title": title}, format="json")

    def test_anonymous_cannot_read_or_create(self):
        self.assertIn(self.client_for().get(URL).status_code, (401, 403))
        self.assertIn(self.create(None).status_code, (401, 403))
        self.assertFalse(LibraryBlock.objects.exists())

    def test_department_role_without_library_right_cannot_create(self):
        self.assertEqual(self.create(self.planner).status_code, 403)
        self.assertFalse(LibraryBlock.objects.exists())

    def test_department_role_with_library_right_creates_and_edits_own_block(self):
        response = self.create(self.department_editor)
        self.assertEqual(response.status_code, 201, response.content)
        block = LibraryBlock.objects.get()
        self.assertEqual(block.created_by, self.department_editor)

        response = self.client_for(self.department_editor).patch(
            f"{URL}{block.pk}/", {"title": "Knoten 2"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        block.refresh_from_db()
        self.assertEqual(block.title, "Knoten 2")

    def test_editor_of_another_department_cannot_change_foreign_block(self):
        block = LibraryBlock.objects.create(title="Knoten", created_by=self.department_editor)
        response = self.client_for(self.foreign_editor).patch(f"{URL}{block.pk}/", {"title": "x"}, format="json")
        self.assertEqual(response.status_code, 403)
        block.refresh_from_db()
        self.assertEqual(block.title, "Knoten")

    def test_department_editor_cannot_delete_or_import(self):
        block = LibraryBlock.objects.create(title="Knoten", created_by=self.department_editor)
        client = self.client_for(self.department_editor)
        self.assertEqual(client.delete(f"{URL}{block.pk}/").status_code, 403)
        response = client.post(f"{URL}import_blocks/", {"jf_manager_version": "1.0", "blocks": []}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(LibraryBlock.objects.filter(pk=block.pk).exists())

    def test_department_editor_cannot_create_taxonomy(self):
        client = self.client_for(self.department_editor)
        self.assertEqual(client.post(f"{URL}tags/", {"name": "Knoten"}, format="json").status_code, 403)
        self.assertEqual(client.post(f"{URL}categories/", {"name": "Spiel"}, format="json").status_code, 403)

    def test_global_editor_changes_any_block(self):
        block = LibraryBlock.objects.create(title="Knoten", created_by=self.department_editor)
        response = self.client_for(self.global_editor).patch(f"{URL}{block.pk}/", {"title": "Neu"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
