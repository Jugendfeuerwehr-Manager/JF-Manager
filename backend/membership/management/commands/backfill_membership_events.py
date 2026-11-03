"""Create the join movement for members that have a join date but no movement yet."""

from django.core.management.base import BaseCommand

from members.models import Member
from membership.models import MembershipEvent
from membership.services import lifecycle


class Command(BaseCommand):
    help = "Legt für Mitglieder mit Eintrittsdatum, aber ohne Zugangsereignis, einen Zugang „neu“ an."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Nur zählen, nichts schreiben.")

    def handle(self, *args, dry_run=False, **options):
        members = (
            Member.objects.filter(joined__isnull=False)
            .exclude(membership_events__kind__in=MembershipEvent.JOIN_KINDS)
            .prefetch_related("departments")
        )
        count = 0
        for member in members.iterator(chunk_size=200):
            count += 1
            if dry_run:
                continue
            lifecycle.admit(member, on=member.joined)
        verb = "würden angelegt" if dry_run else "angelegt"
        self.stdout.write(f"{count} Zugänge {verb}.")
