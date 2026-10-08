from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("training", "0002_trainingsession_department"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="trainingsession",
            options={
                "ordering": ["-date", "start_time"],
                "permissions": [("can_manage_training", "Kann Trainingseinheiten verwalten")],
                "verbose_name": "Trainingseinheit",
                "verbose_name_plural": "Trainingseinheiten",
            },
        ),
        migrations.AlterModelOptions(
            name="libraryblock",
            options={
                "ordering": ["title"],
                "permissions": [("can_manage_library", "Kann Trainingsbibliothek verwalten")],
                "verbose_name": "Bibliotheksblock",
                "verbose_name_plural": "Bibliotheksblöcke",
            },
        ),
    ]
