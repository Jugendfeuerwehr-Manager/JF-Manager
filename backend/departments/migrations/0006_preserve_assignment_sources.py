from django.conf import settings
from django.db import migrations


def preserve_local_sources(apps, schema_editor):
    # Old records carry no reliable provenance. Preserve all as local rather
    # than guessing from mapping names and revoking independent permissions.
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Role = apps.get_model("departments", "UserDepartmentRole")
    Grant = apps.get_model("departments", "RoleGrant")
    alias = schema_editor.connection.alias
    for user in User.objects.using(alias).prefetch_related("groups").iterator(chunk_size=200):
        Grant.objects.using(alias).bulk_create(
            [Grant(user_id=user.pk, group_id=group.pk, source="local") for group in user.groups.all()]
        )
    for role in Role.objects.using(alias).prefetch_related("groups").iterator(chunk_size=200):
        Grant.objects.using(alias).bulk_create(
            [
                Grant(user_id=role.user_id, department_id=role.department_id, group_id=group.pk, source="local")
                for group in role.groups.all()
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0005_alter_roletemplate_options_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [migrations.RunPython(preserve_local_sources, migrations.RunPython.noop)]
