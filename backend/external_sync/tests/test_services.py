import asyncio
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from departments.models import Department
from external_sync.models import SyncBinding, SyncJob
from external_sync.services import SpondExternalSyncProvider
from members.models import Group, Member, Parent


class SyncBindingUpsertTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Nord")
        self.job = SyncJob.objects.create(
            name="Spond Sync",
            provider=SyncJob.Provider.SPOND,
            scope=SyncJob.Scope.DEPARTMENT,
            department=self.department,
        )
        self.provider = SpondExternalSyncProvider()
        self.group = Group.objects.create(name="A-Team", department=self.department)
        self.group_ct = ContentType.objects.get_for_model(Group)

    def test_upsert_binding_remaps_existing_object_binding(self):
        SyncBinding.objects.create(
            job=self.job,
            object_type=SyncBinding.ObjectType.GROUP,
            external_id="legacy-ext-id",
            external_name="A-Team",
            content_type=self.group_ct,
            object_id=self.group.id,
            managed_fields=["name"],
        )

        self.provider._upsert_binding(
            job=self.job,
            object_type=SyncBinding.ObjectType.GROUP,
            external_id="new-ext-id",
            content_type=self.group_ct,
            object_id=self.group.id,
            defaults={
                "external_name": "A-Team Renamed",
                "is_deleted_in_source": False,
                "pending_garbage_collection": False,
                "managed_fields": ["name", "department"],
            },
        )

        self.assertEqual(SyncBinding.objects.count(), 1)
        binding = SyncBinding.objects.get(job=self.job, content_type=self.group_ct, object_id=self.group.id)
        self.assertEqual(binding.external_id, "new-ext-id")
        self.assertEqual(binding.external_name, "A-Team Renamed")
        self.assertFalse(binding.is_deleted_in_source)
        self.assertFalse(binding.pending_garbage_collection)


class SpondFieldMappingTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="West")
        self.job = SyncJob.objects.create(
            name="Spond Sync Fields",
            provider=SyncJob.Provider.SPOND,
            scope=SyncJob.Scope.DEPARTMENT,
            department=self.department,
        )
        self.provider = SpondExternalSyncProvider()

    async def _fake_fetch_groups(self, job):
        return [
            {
                "id": "g-1",
                "name": "Jugend",
                "members": [
                    {
                        "id": "m-1",
                        "firstName": "Max",
                        "lastName": "Mustermann",
                        "email": "max@example.com",
                        "phoneNumber": "+49151111222333",
                        "mobilePhone": "+491701234567",
                        "birthDate": "2010-02-03",
                        "address": {
                            "street": "Hauptstr. 1",
                            "postalCode": "12345",
                            "city": "Berlin",
                        },
                        "guardians": [
                            {
                                "firstName": "Erika",
                                "lastName": "Mustermann",
                                "email": "erika@example.com",
                                "phone": "030123456",
                                "mobilePhone": "+491761234567",
                                "address": {
                                    "street": "Nebenweg 2",
                                    "zipCode": "54321",
                                    "city": "Bonn",
                                },
                            }
                        ],
                    }
                ],
            }
        ]

    def test_run_maps_birthday_phone_and_address(self):
        self.provider._fetch_groups = self._fake_fetch_groups

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Max", lastname="Mustermann")
        self.assertEqual(str(member.birthday), "2010-02-03")
        self.assertEqual(member.phone, "+49151111222333")
        self.assertEqual(member.mobile, "+491701234567")
        self.assertEqual(member.street, "Hauptstr. 1")
        self.assertEqual(member.zip_code, "12345")
        self.assertEqual(member.city, "Berlin")

        parent = Parent.objects.get(name="Erika", lastname="Mustermann")
        self.assertEqual(parent.phone, "030123456")
        self.assertEqual(parent.mobile, "+491761234567")
        self.assertEqual(parent.street, "Nebenweg 2")
        self.assertEqual(parent.zip_code, "54321")
        self.assertEqual(parent.city, "Bonn")

    async def _fake_fetch_groups_list_address(self, job):
        return [
            {
                "id": "g-1-list-address",
                "name": "Jugend List Address",
                "members": [
                    {
                        "id": "m-1-list-address",
                        "firstName": "Lucy",
                        "lastName": "Meyer",
                        "email": "lucy@example.com",
                        "address": ["Carl-Benz-Straße 3", "Laudenbach", "69514", None],
                    }
                ],
            }
        ]

    def test_run_maps_address_when_spond_returns_list_shape(self):
        self.provider._fetch_groups = self._fake_fetch_groups_list_address

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Lucy", lastname="Meyer")
        self.assertEqual(member.street, "Carl-Benz-Straße 3")
        self.assertEqual(member.city, "Laudenbach")
        self.assertEqual(member.zip_code, "69514")

    async def _fake_fetch_groups_invalid_birthday(self, job):
        return [
            {
                "id": "g-2",
                "name": "Jugend 2",
                "members": [
                    {
                        "id": "m-2",
                        "firstName": "Lena",
                        "lastName": "Beispiel",
                        "email": "lena@example.com",
                        "birthDate": "2024-02-31",
                    }
                ],
            }
        ]

    def test_run_ignores_invalid_birthday_values(self):
        self.provider._fetch_groups = self._fake_fetch_groups_invalid_birthday

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Lena", lastname="Beispiel")
        self.assertIsNone(member.birthday)

    async def _fake_fetch_groups_invalid_birthday_day_99(self, job):
        return [
            {
                "id": "g-3",
                "name": "Jugend 3",
                "members": [
                    {
                        "id": "m-3",
                        "firstName": "Tom",
                        "lastName": "Tester",
                        "email": "tom@example.com",
                        "birthDate": "2007-12-99",
                    }
                ],
            }
        ]

    def test_run_ignores_invalid_birthday_day_99(self):
        self.provider._fetch_groups = self._fake_fetch_groups_invalid_birthday_day_99

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Tom", lastname="Tester")
        self.assertEqual(str(member.birthday), "2007-12-01")
        self.assertIn(
            "Genauer Geburtstag wurde von Spond nicht übergeben. es wurde der 01. als Tag gesetzt.",
            member.notes,
        )

    def test_run_continues_when_date_parser_raises(self):
        self.provider._fetch_groups = self._fake_fetch_groups_invalid_birthday

        with patch.object(self.provider, "_parse_birthday", side_effect=ValueError("day is out of range for month")):
            self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Lena", lastname="Beispiel")
        self.assertIsNone(member.birthday)

    def test_filter_groups_by_selected_top_level_group(self):
        groups = [
            {"id": "top-1", "name": "Top 1"},
            {"id": "sub-1", "name": "Sub 1", "parentGroupId": "top-1"},
            {"id": "top-2", "name": "Top 2"},
        ]

        selected = self.provider._filter_groups_by_top_level(groups, top_level_group_id="top-1")

        self.assertEqual({group["id"] for group in selected}, {"top-1", "sub-1"})

    def test_list_top_level_groups_only_returns_root_nodes(self):
        async def fake_fetch_all_groups(username, password):
            return [
                {"id": "sub-1", "name": "Sub 1", "parentGroupId": "top-1"},
                {"id": "top-2", "name": "Top B"},
                {"id": "top-1", "name": "Top A"},
            ]

        with patch.object(self.provider, "_fetch_all_groups", side_effect=fake_fetch_all_groups):
            top_level_groups = self.provider.list_top_level_groups({"username": "u", "password": "p"})

        self.assertEqual(top_level_groups, [{"id": "top-1", "name": "Top A"}, {"id": "top-2", "name": "Top B"}])

    def test_fetch_groups_uses_selected_top_level_group(self):
        async def fake_fetch_all_groups(username, password):
            return [
                {"id": "top-1", "name": "Top 1"},
                {"id": "sub-1", "name": "Sub 1", "parentGroupId": "top-1"},
                {"id": "top-2", "name": "Top 2"},
            ]

        self.job.config = {"group_id": "top-1"}
        self.job.credentials = {"username": "u", "password": "p"}

        with patch.object(self.provider, "_fetch_all_groups", side_effect=fake_fetch_all_groups):
            selected_groups = asyncio.run(self.provider._fetch_groups(self.job))

        self.assertEqual({group["id"] for group in selected_groups}, {"top-1", "sub-1"})

    async def _fake_fetch_groups_with_nested_subgroups(self, job):
        return [
            {
                "id": "top-1",
                "name": "Department Top",
                "subGroups": [
                    {
                        "id": "sub-1",
                        "name": "Group A",
                        "members": [
                            {
                                "id": "m-10",
                                "firstName": "Nina",
                                "lastName": "Nested",
                                "email": "nina@example.com",
                            }
                        ],
                    }
                ],
            }
        ]

    def test_run_creates_local_groups_from_subgroups_and_assigns_members(self):
        self.provider._fetch_groups = self._fake_fetch_groups_with_nested_subgroups

        self.provider.run(job=self.job, triggered_by=None)

        self.assertFalse(Group.objects.filter(name="Department Top").exists())
        subgroup = Group.objects.get(name="Group A")
        member = Member.objects.get(name="Nina", lastname="Nested")
        self.assertEqual(member.group_id, subgroup.id)

    async def _fake_fetch_groups_top_level_members_with_subgroup_ids(self, job):
        return [
            {
                "id": "top-1",
                "name": "Department Top",
                "members": [
                    {
                        "id": "m-20",
                        "firstName": "Paul",
                        "lastName": "Primary",
                        "email": "paul@example.com",
                        "groupIds": ["sub-2", "sub-1", "top-1"],
                    }
                ],
            },
            {
                "id": "sub-1",
                "name": "Group A",
                "parentGroupId": "top-1",
                "members": [],
            },
            {
                "id": "sub-2",
                "name": "Group B",
                "parentGroupId": "top-1",
                "members": [],
            },
        ]

    def test_run_assigns_top_level_member_to_first_payload_subgroup(self):
        self.provider._fetch_groups = self._fake_fetch_groups_top_level_members_with_subgroup_ids

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Paul", lastname="Primary")
        self.assertEqual(member.group.name, "Group B")

    async def _fake_fetch_groups_top_level_members_with_subgroups_key(self, job):
        return [
            {
                "id": "top-3",
                "name": "Department Top 3",
                "members": [
                    {
                        "id": "227F39AC4F4743E5A7C89BE3B3BC70B4",
                        "firstName": "Finley",
                        "lastName": "Goldhorn",
                        "subGroups": ["4CBDC8615D1740ECA40F814DC87B794E"],
                    }
                ],
            },
            {
                "id": "4CBDC8615D1740ECA40F814DC87B794E",
                "name": "Group Finley",
                "parentGroupId": "top-3",
                "members": [],
            },
        ]

    def test_run_assigns_member_using_subgroups_key(self):
        self.provider._fetch_groups = self._fake_fetch_groups_top_level_members_with_subgroups_key

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Finley", lastname="Goldhorn")
        self.assertEqual(member.group.name, "Group Finley")

    async def _fake_fetch_groups_nested_subgroups_with_top_level_members(self, job):
        return [
            {
                "id": "top-9",
                "name": "Department Top 9",
                "members": [
                    {
                        "id": "m-90",
                        "firstName": "Mila",
                        "lastName": "Main",
                        "subGroups": ["sub-9"],
                    }
                ],
                "subGroups": [
                    {
                        "id": "sub-9",
                        "name": "Group Nine",
                        "members": [],
                    }
                ],
            }
        ]

    def test_run_assigns_top_level_member_when_group_contains_nested_subgroups(self):
        self.provider._fetch_groups = self._fake_fetch_groups_nested_subgroups_with_top_level_members

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Mila", lastname="Main")
        self.assertEqual(member.group.name, "Group Nine")

    async def _fake_fetch_groups_member_subgroups_as_objects(self, job):
        return [
            {
                "id": "top-10",
                "name": "Department Top 10",
                "members": [
                    {
                        "id": "m-100",
                        "firstName": "Noah",
                        "lastName": "Objects",
                        "subGroups": [{"id": "sub-10", "name": "Group Ten"}],
                    }
                ],
            },
            {
                "id": "sub-10",
                "name": "Group Ten",
                "parentGroupId": "top-10",
                "members": [],
            },
        ]

    def test_run_assigns_member_using_subgroups_object_payload(self):
        self.provider._fetch_groups = self._fake_fetch_groups_member_subgroups_as_objects

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Noah", lastname="Objects")
        self.assertEqual(member.group.name, "Group Ten")

    async def _fake_fetch_groups_for_members_only_sync(self, job):
        return [
            {
                "id": "top-20",
                "name": "Department Top 20",
                "members": [
                    {
                        "id": "m-200",
                        "firstName": "Mia",
                        "lastName": "MemberOnly",
                        "email": "mia@example.com",
                        "subGroups": ["sub-20"],
                    }
                ],
                "subGroups": [
                    {
                        "id": "sub-20",
                        "name": "Group 20",
                        "members": [],
                    }
                ],
            }
        ]

    def test_run_members_only_sync_skips_group_creation_and_assignment(self):
        self.provider._fetch_groups = self._fake_fetch_groups_for_members_only_sync
        self.job.config = {"group_id": "top-20", "sync_groups": False}
        self.job.save(update_fields=["config"])

        self.provider.run(job=self.job, triggered_by=None)

        member = Member.objects.get(name="Mia", lastname="MemberOnly")
        self.assertIsNone(member.group)
        self.assertFalse(Group.objects.filter(name="Department Top 20").exists())
        self.assertFalse(Group.objects.filter(name="Group 20").exists())
        self.assertFalse(SyncBinding.objects.filter(job=self.job, object_type=SyncBinding.ObjectType.GROUP).exists())

    async def _fake_fetch_groups_for_department_mode(self, job):
        return [
            {
                "id": "top-30",
                "name": "Department Top 30",
                "subGroups": [
                    {
                        "id": "sub-30-a",
                        "name": "Jugend Mitte",
                        "members": [
                            {
                                "id": "m-300",
                                "firstName": "Mara",
                                "lastName": "Dept",
                                "email": "mara@example.com",
                                "subGroups": ["sub-30-a", "sub-30-b"],
                            }
                        ],
                    },
                    {
                        "id": "sub-30-b",
                        "name": "Jugend Nord",
                        "members": [],
                    },
                ],
            }
        ]

    def test_run_groups_to_departments_creates_departments_and_assigns_members(self):
        self.provider._fetch_groups = self._fake_fetch_groups_for_department_mode
        self.job.scope = SyncJob.Scope.ORGANIZATION
        self.job.department = None
        self.job.config = {"group_id": "top-30", "operation_mode": "groups_to_departments"}
        self.job.save(update_fields=["scope", "department", "config"])

        result = self.provider.run(job=self.job, triggered_by=None)

        mara = Member.objects.get(name="Mara", lastname="Dept")
        self.assertIsNone(mara.group)
        self.assertEqual(mara.departments.filter(name="Jugend Mitte").count(), 1)
        self.assertEqual(mara.departments.filter(name="Jugend Nord").count(), 1)

        self.assertTrue(Department.objects.filter(name="Jugend Mitte").exists())
        self.assertTrue(Department.objects.filter(name="Jugend Nord").exists())
        self.assertEqual(
            SyncBinding.objects.filter(job=self.job, object_type=SyncBinding.ObjectType.DEPARTMENT).count(),
            2,
        )
        self.assertEqual(result["imported_departments"], 2)
