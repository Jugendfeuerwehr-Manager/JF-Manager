from django.core.management.base import BaseCommand
from django.utils import timezone

from privacy.services.retention import purge_personal_data


class Command(BaseCommand):
    help = "Personenbezogene Daten nach den Aufbewahrungsfristen (Einstellungen > Datenschutz) löschen; täglich."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Nur zählen, nichts löschen.")

    def handle(self, *args, dry_run=False, **options):
        verb = "Würden bereinigt" if dry_run else "Bereinigt"
        for result in purge_personal_data(dry_run=dry_run):
            cutoff = timezone.localtime(result.cutoff)
            self.stdout.write(f"{verb}: {result.count} – {result.label} (älter als {cutoff:%d.%m.%Y})")
