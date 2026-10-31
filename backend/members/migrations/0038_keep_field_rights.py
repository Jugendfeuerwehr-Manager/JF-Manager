from django.contrib.auth.management import create_permissions
from django.db import migrations


def keep_current_visibility(apps, schema_editor):
    """Field rights are new: groups and accounts that could read members keep seeing
    contact data and notes; editors also get health notes so they can maintain them.
    Need-to-know for the standard roles follows via reconcile_role_groups."""
    app_config = apps.get_app_config("members")
    app_config.models_module = True
    create_permissions(app_config, apps=apps, verbosity=0)
    app_config.models_module = None
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("users", "CustomUser")

    def perm(codename):
        return Permission.objects.get(content_type__app_label="members", codename=codename)

    view, change = perm("view_member"), perm("change_member")
    readable = [perm("view_member_contact"), perm("view_member_sensitive")]
    health = perm("view_member_health")
    for group in Group.objects.filter(permissions=view).distinct():
        group.permissions.add(*readable)
    for group in Group.objects.filter(permissions=change).distinct():
        group.permissions.add(health)
    for user in User.objects.filter(user_permissions=view).distinct():
        user.user_permissions.add(*readable)
    for user in User.objects.filter(user_permissions=change).distinct():
        user.user_permissions.add(health)


class Migration(migrations.Migration):
    dependencies = [
        ("members", "0037_member_field_rights_health"),
        ("users", "0016_remove_dsgvo_flags"),
    ]

    operations = [migrations.RunPython(keep_current_visibility, migrations.RunPython.noop)]
