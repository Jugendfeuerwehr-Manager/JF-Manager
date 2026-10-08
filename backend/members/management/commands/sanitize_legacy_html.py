"""Idempotently clean stored rich text without logging its contents."""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from jf_manager_backend.html_safety import sanitize_rich_html


class Command(BaseCommand):
    help = "Prüft gespeicherten Rich Text; --apply migriert ihn atomar. Vorher Datenbank sichern."
    fields = (
        ("users", "CustomUser", "email_signature"),
        ("members", "EmailMessage", "body_html"),
        ("members", "EmailRecipient", "personalized_body_html"),
        ("training", "TrainingBlock", "content"),
        ("training", "LibraryBlock", "content"),
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Bereinigungen dauerhaft speichern.")

    @transaction.atomic
    def handle(self, *args, **options):
        apply = options["apply"]
        for app, model_name, field in self.fields:
            model = apps.get_model(app, model_name)
            rows = model.objects.all().order_by("pk")
            if apply:
                rows = rows.select_for_update()
            changed = 0
            for row in rows.only("pk", field).iterator():
                original = getattr(row, field)
                cleaned = sanitize_rich_html(original)
                if original != cleaned:
                    changed += 1
                    if apply:
                        model.objects.filter(pk=row.pk).update(**{field: cleaned})
            self.stdout.write(f"{app}.{model_name}.{field}: {changed} {'migriert' if apply else 'zu bereinigen'}")
