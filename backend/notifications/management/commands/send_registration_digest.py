from django.core.management.base import BaseCommand

from notifications.account_producers import registration_digest


class Command(BaseCommand):
    help = "Tageszusammenfassung der Meldungen an die Dienstverantwortlichen einreihen (NOTIF-01.5c)."

    def handle(self, *args, **options):
        self.stdout.write(f"Zusammenfassungen eingereiht: {registration_digest()}")
