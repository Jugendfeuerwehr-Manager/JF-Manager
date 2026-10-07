"""Console reset of the second factor (SEC-11.3).

Works for every account, including superusers and staff, whose MFA cannot be
reset in the web interface. Run through jfctl on production systems:
    jfctl admin reset-mfa --user NAME
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from users.mfa import reset_mfa


class Command(BaseCommand):
    help = "Zwei-Faktor-Anmeldung (Authenticator-App, Passkeys, Wiederherstellungscodes) eines Kontos zurücksetzen."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Benutzername des Kontos")

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options["user"]).first()
        if user is None:
            raise CommandError("Benutzer nicht gefunden.")
        result = reset_mfa(user, channel="console")
        self.stdout.write(
            self.style.SUCCESS(
                f"Zwei-Faktor-Anmeldung zurückgesetzt: Authenticator {result['totp']}, Passkeys {result['passkeys']}, "
                f"Wiederherstellungscodes {result['recovery_codes']}, beendete Sitzungen {result['sessions']}."
            )
        )
        self.stdout.write("Das Konto richtet MFA bei der nächsten Anmeldung neu ein.")
