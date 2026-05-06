import json

import django_rq
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from external_sync.models import SyncJob, SyncRun


@django_rq.job("default")
def run_sync_job(job_id: int) -> dict:
    """
    RQ task: run a single SyncJob identified by *job_id*.

    Records a SyncRun with the result or marks the run as FAILED on any error.
    Returns the summary dict so callers/tests can inspect results.
    """
    try:
        job = SyncJob.objects.get(pk=job_id)
    except SyncJob.DoesNotExist:
        return {"error": f"SyncJob {job_id} not found"}

    from external_sync.services import ProviderNotImplementedError, get_provider  # local import avoids circular

    started_at = timezone.now()
    try:
        provider = get_provider(job.provider)
        result = provider.run(job=job, triggered_by=None)
        summary = json.loads(json.dumps(result, cls=DjangoJSONEncoder))
        run = SyncRun.objects.create(
            job=job,
            triggered_by=None,
            status=SyncRun.Status.SUCCEEDED,
            trigger="scheduled",
            started_at=result.get("started_at", started_at),
            finished_at=result.get("finished_at", timezone.now()),
            summary=summary,
            imported_members=result.get("imported_members", 0),
            imported_groups=result.get("imported_groups", 0),
            updated_members=result.get("updated_members", 0),
            updated_groups=result.get("updated_groups", 0),
            flagged_for_review=result.get("flagged_for_review", 0),
            deleted_objects=result.get("deleted_objects", 0),
        )
        job.last_run_at = run.finished_at
        job.last_success_at = run.finished_at
        job.last_error = ""
        job.save(update_fields=["last_run_at", "last_success_at", "last_error", "updated_at"])
        return result
    except (ProviderNotImplementedError, Exception) as exc:
        error_msg = str(exc)
        now = timezone.now()
        SyncRun.objects.create(
            job=job,
            triggered_by=None,
            status=SyncRun.Status.FAILED,
            trigger="scheduled",
            started_at=started_at,
            finished_at=now,
            error_message=error_msg,
            summary={"provider": job.provider, "error": error_msg},
        )
        job.last_run_at = now
        job.last_error = error_msg
        job.save(update_fields=["last_run_at", "last_error", "updated_at"])
        return {"error": error_msg}
