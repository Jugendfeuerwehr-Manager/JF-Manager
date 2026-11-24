from django.db import migrations

KINDS = (
    (
        "data_processing_applicant",
        "Datenspeicherung zu Verwaltungszwecken",
        "Ich bin damit einverstanden, dass die hier angegebenen persönlichen Daten zu Verwaltungszwecken "
        "in die Mitgliederverwaltung aufgenommen und gespeichert werden.",
    ),
    (
        "consent_continues_ea",
        "Fortgeltung bei Übertritt in die Einsatzabteilung",
        "Die Einwilligungen gelten auch über das 18. Lebensjahr hinaus mit dem Übertritt in die "
        "Einsatzabteilung weiter.",
    ),
)


def seed(apps, schema_editor):
    ConsentKind = apps.get_model("privacy", "ConsentKind")
    position = ConsentKind.objects.count()
    for offset, (slug, label, description) in enumerate(KINDS):
        ConsentKind.objects.get_or_create(
            slug=slug,
            defaults={
                "label": label,
                "description": description,
                "in_portal": False,
                "active": True,
                "built_in": True,
                "position": position + offset,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("admissions", "0001_initial"),
        ("privacy", "0005_consent_kind_portal_terms"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
