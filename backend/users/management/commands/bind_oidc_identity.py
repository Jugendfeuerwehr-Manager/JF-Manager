"""Explicit, operator-controlled migration of an existing OIDC identity."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction


class Command(BaseCommand):
    help = "Bind an existing OIDC account to its independently verified provider issuer and subject."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("issuer")
        parser.add_argument("subject")

    @transaction.atomic
    def handle(self, *args, **options):
        user = (
            get_user_model()
            .objects.select_for_update()
            .filter(username=options["username"], auth_source="oidc")
            .first()
        )
        if not user:
            raise CommandError("Das vorhandene Konto muss auth_source=oidc haben.")
        if user.oidc_subject:
            raise CommandError("Das Konto ist bereits gebunden. Bestehende Bindungen werden nicht überschrieben.")
        if not options["issuer"].startswith("https://") or not options["subject"]:
            raise CommandError("HTTPS-Issuer und nichtleeres Subject erforderlich.")
        user.oidc_issuer = options["issuer"].rstrip("/")
        user.oidc_subject = options["subject"]
        try:
            user.save(update_fields=["oidc_issuer", "oidc_subject"])
        except IntegrityError as exc:
            raise CommandError("Diese OIDC-Identität ist bereits einem anderen Konto zugeordnet.") from exc
        self.stdout.write(self.style.SUCCESS("OIDC-Identität wurde gebunden."))
