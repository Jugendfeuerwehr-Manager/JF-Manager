"""UX-03.2: versioned check-off with conflict answers and previewed bulk actions."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member, MemberList, MemberListEntry
from members.services.member_list_entries import EntryVersionConflict, set_entry_check


def _role(user, department, codenames, name):
    group = Group.objects.create(name=name)
    group.permissions.add(*Permission.objects.filter(content_type__app_label="members", codename__in=codenames))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class MemberListVersioningTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="Version A", code="version-a")
        cls.department_b = Department.objects.create(name="Version B", code="version-b")
        cls.anna = Member.objects.create(name="Anna", lastname="Albers")
        cls.ben = Member.objects.create(name="Ben", lastname="Brandt")
        cls.cleo = Member.objects.create(name="Cleo", lastname="Conrad")
        for member in (cls.anna, cls.ben, cls.cleo):
            member.departments.add(cls.department_a)
        cls.foreign = Member.objects.create(name="Fremd", lastname="Person")
        cls.foreign.departments.add(cls.department_b)
        cls.list_a = MemberList.objects.create(name="Packliste", department=cls.department_a)
        cls.list_b = MemberList.objects.create(name="Fremde Liste", department=cls.department_b)
        cls.entry_anna = MemberListEntry.objects.create(member_list=cls.list_a, member=cls.anna)
        cls.entry_ben = MemberListEntry.objects.create(member_list=cls.list_a, member=cls.ben, checked=True)
        cls.entry_foreign = MemberListEntry.objects.create(member_list=cls.list_b, member=cls.foreign)

        users = get_user_model().objects
        cls.editor = users.create_user(username="version-editor", password="test-only-password")
        _role(cls.editor, cls.department_a, ["view_memberlist", "change_memberlist"], "Version editor A")
        cls.reader = users.create_user(username="version-reader", password="test-only-password")
        _role(cls.reader, cls.department_a, ["view_memberlist"], "Version reader A")

    def setUp(self):
        self.client.force_authenticate(self.editor)

    def _post(self, member_list, action, data, method="post"):
        return getattr(self.client, method)(f"/api/v1/member-lists/{member_list.pk}/{action}/", data, format="json")

    def test_detail_exposes_entry_versions(self):
        response = self.client.get(f"/api/v1/member-lists/{self.list_a.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({entry["version"] for entry in response.data["entries"]}, {1})

    def test_matching_version_saves_and_raises_the_version(self):
        response = self._post(
            self.list_a, "set_check", {"member_id": self.anna.pk, "checked": True, "expected_version": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], 2)
        self.assertTrue(response.data["checked"])
        self.entry_anna.refresh_from_db()
        self.assertEqual((self.entry_anna.checked, self.entry_anna.version), (True, 2))

    def test_stale_version_answers_conflict_with_current_state(self):
        self._post(self.list_a, "set_check", {"member_id": self.anna.pk, "checked": True, "expected_version": 1})
        response = self._post(
            self.list_a, "set_check", {"member_id": self.anna.pk, "checked": False, "expected_version": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "conflict")
        self.assertEqual(response.data["current"]["member_id"], self.anna.pk)
        self.assertTrue(response.data["current"]["checked"])
        self.assertEqual(response.data["current"]["version"], 2)
        self.entry_anna.refresh_from_db()
        self.assertTrue(self.entry_anna.checked)

    def test_reaching_the_same_state_is_not_a_conflict(self):
        self._post(self.list_a, "set_check", {"member_id": self.anna.pk, "checked": True, "expected_version": 1})
        response = self._post(
            self.list_a, "set_check", {"member_id": self.anna.pk, "checked": True, "expected_version": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], 2)

    def test_stale_toggle_and_note_are_refused(self):
        self._post(self.list_a, "set_check", {"member_id": self.ben.pk, "checked": False, "expected_version": 1})
        toggle = self._post(self.list_a, "toggle_check", {"member_id": self.ben.pk, "expected_version": 1})
        self.assertEqual(toggle.status_code, status.HTTP_409_CONFLICT)
        notes = self._post(
            self.list_a,
            "update_entry_notes",
            {"member_id": self.ben.pk, "notes": "Neu", "expected_version": 1},
            "patch",
        )
        self.assertEqual(notes.status_code, status.HTTP_409_CONFLICT)
        current = self._post(
            self.list_a,
            "update_entry_notes",
            {"member_id": self.ben.pk, "notes": "Neu", "expected_version": 2},
            "patch",
        )
        self.assertEqual(current.status_code, status.HTTP_200_OK)
        self.assertEqual((current.data["notes"], current.data["version"]), ("Neu", 3))

    def test_write_without_version_stays_compatible(self):
        response = self._post(self.list_a, "toggle_check", {"member_id": self.anna.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["checked"])

    def test_unknown_member_is_not_found(self):
        response = self._post(self.list_a, "set_check", {"member_id": self.foreign.pk, "checked": True})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_check_preview_writes_nothing_and_names_the_affected(self):
        response = self._post(self.list_a, "check_all", {"dry_run": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["entries"][0]["name"], self.anna.get_full_name())
        self.assertFalse(MemberListEntry.objects.get(pk=self.entry_anna.pk).checked)

    def test_bulk_check_requires_the_previewed_selection(self):
        response = self._post(self.list_a, "check_all", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(MemberListEntry.objects.get(pk=self.entry_anna.pk).checked)

    def test_bulk_check_changes_only_previewed_entries(self):
        cleo_entry = MemberListEntry.objects.create(member_list=self.list_a, member=self.cleo)
        response = self._post(self.list_a, "check_all", {"member_ids": [self.anna.pk]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual((response.data["changed"], response.data["skipped"]), (1, 0))
        cleo_entry.refresh_from_db()
        self.assertFalse(cleo_entry.checked)
        self.entry_anna.refresh_from_db()
        self.assertEqual((self.entry_anna.checked, self.entry_anna.version), (True, 2))
        self.assertEqual(response.data["checked_count"], 2)

    def test_bulk_uncheck_skips_entries_changed_since_the_preview(self):
        preview = self._post(self.list_a, "uncheck_all", {"dry_run": True})
        self.assertEqual([entry["member_id"] for entry in preview.data["entries"]], [self.ben.pk])
        set_entry_check(self.list_a, self.ben.pk, False)
        response = self._post(self.list_a, "uncheck_all", {"member_ids": [self.ben.pk]})
        self.assertEqual((response.data["changed"], response.data["skipped"]), (0, 1))
        self.entry_ben.refresh_from_db()
        self.assertEqual(self.entry_ben.version, 2)

    def test_bulk_add_preview_names_new_members_without_writing(self):
        response = self._post(self.list_a, "bulk_add", {"member_ids": [self.ben.pk, self.cleo.pk], "dry_run": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["members"], [{"member_id": self.cleo.pk, "name": self.cleo.get_full_name()}])
        self.assertEqual(response.data["already_in_list"], 1)
        self.assertFalse(MemberListEntry.objects.filter(member_list=self.list_a, member=self.cleo).exists())

    def test_bulk_add_preview_rejects_foreign_members(self):
        response = self._post(self.list_a, "bulk_add", {"member_ids": [self.foreign.pk], "dry_run": True})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_read_only_role_cannot_check_or_preview(self):
        self.client.force_authenticate(self.reader)
        for action, data in (
            ("set_check", {"member_id": self.anna.pk, "checked": True, "expected_version": 1}),
            ("check_all", {"dry_run": True}),
            ("bulk_add", {"member_ids": [self.cleo.pk], "dry_run": True}),
        ):
            with self.subTest(action=action):
                self.assertEqual(self._post(self.list_a, action, data).status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(MemberListEntry.objects.get(pk=self.entry_anna.pk).checked)

    def test_foreign_department_list_reveals_nothing(self):
        for action, data in (
            ("set_check", {"member_id": self.foreign.pk, "checked": True, "expected_version": 1}),
            ("uncheck_all", {"dry_run": True}),
            ("check_all", {"dry_run": True}),
        ):
            with self.subTest(action=action):
                response = self._post(self.list_b, action, data)
                self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
                self.assertNotIn("Fremd", str(response.data))
        self.assertFalse(MemberListEntry.objects.get(pk=self.entry_foreign.pk).checked)

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(None)
        response = self._post(self.list_a, "set_check", {"member_id": self.anna.pk, "checked": True})
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


@skipUnless(connection.vendor == "postgresql", "Row locking of list entries requires PostgreSQL")
class MemberListCheckConcurrencyTests(TransactionTestCase):
    def setUp(self):
        department = Department.objects.create(name="Parallel", code="parallel")
        member = Member.objects.create(name="Paula", lastname="Parallel")
        member.departments.add(department)
        self.member_list = MemberList.objects.create(name="Parallel", department=department)
        self.entry = MemberListEntry.objects.create(member_list=self.member_list, member=member)

    def _parallel(self, targets):
        barrier = Barrier(len(targets))

        def write(target):
            close_old_connections()
            try:
                barrier.wait(timeout=20)
                try:
                    set_entry_check(self.member_list, self.entry.member_id, target, expected_version=1)
                    return "saved"
                except EntryVersionConflict as exc:
                    return ("conflict", exc.entry.version)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(targets)) as executor:
            return list(executor.map(write, targets))

    def test_opposite_writes_on_the_same_version_let_exactly_one_win(self):
        results = self._parallel([True, False, True, False, True, False])
        self.entry.refresh_from_db()
        # Unticking an unticked entry is a no-op success; every tick after the
        # first sees version 2 and must be refused, never applied twice.
        self.assertEqual(self.entry.version, 2)
        self.assertTrue(self.entry.checked)
        conflicts = [result for result in results if result != "saved"]
        self.assertTrue(all(result == ("conflict", 2) for result in conflicts))

    def test_twenty_parallel_toggles_on_one_version_change_the_entry_once(self):
        results = self._parallel([None] * 20)
        self.entry.refresh_from_db()
        self.assertEqual(results.count("saved"), 1)
        self.assertEqual(self.entry.version, 2)
        self.assertTrue(self.entry.checked)
