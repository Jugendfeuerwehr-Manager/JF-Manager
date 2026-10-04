import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0003_department_color"),
        ("members", "0026_emailmessage_recipient_members_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="memberlist",
            name="department",
            field=models.ForeignKey(
                blank=True,
                help_text="Ohne Abteilung nur für ungeklärte Altlisten während der Migration.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="member_lists",
                to="departments.department",
                verbose_name="Abteilung",
            ),
        ),
    ]
