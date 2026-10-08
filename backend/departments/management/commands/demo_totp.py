"""Show the current authenticator code of a seeded demo account (development and demonstrations only)."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from departments.management.commands.seed_demo import DEMO_DOMAIN


class Command(BaseCommand):
    help = "Zeigt den aktuellen Anmeldecode eines Demokontos aus seed_demo."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        from users.mfa import current_step, totp_at
        from users.models import MFADevice

        if not settings.DEBUG:
            raise CommandError("demo_totp ist nur mit DEBUG=True verfügbar.")
        user = get_user_model().objects.filter(username=options["username"]).first()
        # Real accounts never qualify: only seeded demo accounts carry the reserved domain.
        if user is None or not user.email.endswith(f"@{DEMO_DOMAIN}"):
            raise CommandError("Kein Demokonto mit diesem Benutzernamen.")
        device = MFADevice.objects.filter(user=user, confirmed_at__isnull=False).first()
        if device is None:
            raise CommandError("Für dieses Demokonto ist keine Authenticator-App hinterlegt.")
        self.stdout.write(totp_at(device.secret, current_step()))
