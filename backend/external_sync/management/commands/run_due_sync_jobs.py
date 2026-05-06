from django.core.management.base import BaseCommand
from django.utils import timezone

from external_sync.models import SyncJob


class Command(BaseCommand):
    help = "Enqueue all enabled SyncJobs whose next_run_at is in the past (interval-based jobs)."

    def handle(self, *args, **options):
        from external_sync.tasks import run_sync_job  # local import avoids import-time RQ dependency

        now = timezone.now()
        due_jobs = SyncJob.objects.filter(
            enabled=True,
            run_mode=SyncJob.RunMode.INTERVAL,
            next_run_at__lte=now,
        )

        enqueued = 0
        for job in due_jobs:
            run_sync_job.delay(job.pk)
            # Advance next_run_at immediately to prevent double-queueing.
            if job.interval_minutes:
                job.next_run_at = now + timezone.timedelta(minutes=job.interval_minutes)
                job.save(update_fields=["next_run_at", "updated_at"])
            enqueued += 1

        self.stdout.write(self.style.SUCCESS(f"Enqueued {enqueued} sync job(s)."))
