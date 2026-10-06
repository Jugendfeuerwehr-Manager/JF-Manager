from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class RoleSourceMigrationTests(TransactionTestCase):
    def test_legacy_global_and_department_assignments_are_preserved_without_staff_upgrade(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        user_leaves = [node for node in leaves if node[0] == "users"]
        before = [("departments", "0005_alter_roletemplate_options_and_more"), *user_leaves]
        executor.migrate(before)
        apps = executor.loader.project_state(before).apps
        User = apps.get_model("users", "CustomUser")
        Group = apps.get_model("auth", "Group")
        Department = apps.get_model("departments", "Department")
        Role = apps.get_model("departments", "UserDepartmentRole")
        user = User.objects.create(username="synthetic-migration", is_staff=True)
        staff = User.objects.create(username="synthetic-empty-staff", is_staff=True)
        global_group = Group.objects.create(name="Synthetic legacy global")
        scoped_group = Group.objects.create(name="Synthetic legacy scoped")
        department = Department.objects.create(name="Synthetic migration", code="source-migration")
        user.groups.add(global_group)
        Role.objects.create(user=user, department=department).groups.add(scoped_group)
        after = [("departments", "0006_preserve_assignment_sources"), *user_leaves]
        executor = MigrationExecutor(connection)
        executor.migrate(after)
        apps = executor.loader.project_state(after).apps
        Grant = apps.get_model("departments", "RoleGrant")
        self.assertEqual(
            set(Grant.objects.filter(user_id=user.pk).values_list("group_id", "department_id", "source", "source_key")),
            {(global_group.pk, None, "local", ""), (scoped_group.pk, department.pk, "local", "")},
        )
        self.assertFalse(Grant.objects.filter(user_id=staff.pk).exists())
        self.assertEqual(apps.get_model("users", "CustomUser").objects.get(pk=user.pk).groups.get().pk, global_group.pk)
        self.assertEqual(
            apps.get_model("departments", "UserDepartmentRole").objects.get(user_id=user.pk).groups.get().pk,
            scoped_group.pk,
        )
