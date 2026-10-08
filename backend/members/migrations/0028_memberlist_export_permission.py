from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("members", "0027_memberlist_department")]

    operations = [
        migrations.AlterModelOptions(
            name="memberlist",
            options={
                "ordering": ["name"],
                "permissions": [("export_memberlist", "Kann Mitgliederlisten exportieren")],
                "verbose_name": "Mitgliederliste",
                "verbose_name_plural": "Mitgliederlisten",
            },
        ),
    ]
