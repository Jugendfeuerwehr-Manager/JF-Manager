from django.core.management.base import BaseCommand

from notifications.inbox import purge


class Command(BaseCommand):
    help = "Erledigte Aufgaben und gelesene Hinweise im Eingang nach 180 Tagen löschen (NOTIF-01)."

    def handle(self, *args, **options):
        self.stdout.write(f"Gelöschte Eingangseinträge: {purge()}")
