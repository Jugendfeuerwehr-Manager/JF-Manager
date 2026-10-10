from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from members.models import ExportAudit


class Command(BaseCommand):
    help = "Löscht Export-Audits nach AUDIT_RETENTION_DAYS (Standard 180). Täglich einplanen."

    def handle(self, *args, **options):
        count, _ = ExportAudit.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=settings.AUDIT_RETENTION_DAYS)
        ).delete()
        self.stdout.write(f"{count} abgelaufene Export-Audits gelöscht.")
