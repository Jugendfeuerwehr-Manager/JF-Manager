from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from participation.models import Registration

RETENTION_DAYS = 90


class Command(BaseCommand):
    help = "Abmelde-Kurztexte 90 Tage nach dem Dienst löschen (PART-01.4, D4); täglich."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Nur zählen, nichts löschen.")

    def handle(self, *args, dry_run=False, **options):
        cutoff = timezone.localdate() - timedelta(days=RETENTION_DAYS)
        queryset = Registration.objects.exclude(reason_note="").filter(session__date__lt=cutoff)
        count = queryset.count() if dry_run else queryset.update(reason_note="")
        verb = "Würden gelöscht" if dry_run else "Gelöscht"
        self.stdout.write(f"{verb}: {count} Kurztexte (Dienste vor dem {cutoff:%d.%m.%Y}).")
