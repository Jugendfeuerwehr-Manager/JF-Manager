import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from notifications.services import deliver_pending


class Command(BaseCommand):
    help = "Send queued Web Push notifications; --loop runs a worker every 15 seconds."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")

    def handle(self, *args, **options):
        try:
            while True:
                close_old_connections()
                count = deliver_pending()
                if count:
                    self.stdout.write(f"{count} Mitteilungen versendet.")
                if not options["loop"]:
                    return
                time.sleep(15)
        except KeyboardInterrupt:
            return
