from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import StockBookingRequest


class Command(BaseCommand):
    help = (
        "Löscht gespeicherte Antworten für Idempotenzkennungen nach BOOKING_REPLAY_RETENTION_DAYS "
        "(Standard 30). Täglich einplanen. Buchungen selbst bleiben unverändert."
    )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=settings.BOOKING_REPLAY_RETENTION_DAYS)
        count, _ = StockBookingRequest.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(f"{count} abgelaufene Wiederholungsantworten gelöscht.")
