from django.core.management.base import BaseCommand

from portal.lifecycle import daily


class Command(BaseCommand):
    help = "Elternzugänge beenden, deren Kinder alle volljährig sind (ohne Verlängerung); täglich (PORTAL-01.4)."

    def handle(self, *args, **options):
        result = daily()
        self.stdout.write(
            f"Beendete Elternzugänge: {len(result['ended_accounts'])}; "
            f"Elternzugriff endet in 30 Tagen für {len(result['children_ending_soon'])} Kinder."
        )
