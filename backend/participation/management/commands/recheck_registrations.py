from django.core.management.base import BaseCommand

from participation.conflicts import recheck


class Command(BaseCommand):
    help = "Teilnahmevoraussetzungen aktiver Meldungen kommender Dienste nachprüfen (PART-03.5, E11); täglich."

    def handle(self, *args, **options):
        result = recheck()
        self.stdout.write(
            f"Geprüft: {result.checked} Meldungen, neu im Konflikt: {len(result.conflicted)}, "
            f"Konflikt aufgehoben: {len(result.resolved)}."
        )
