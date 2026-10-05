from django.db import models


class ExportAudit(models.Model):
    """Security metadata only: no exported values, names, filters or filenames."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_id = models.PositiveBigIntegerField(null=True)
    action = models.CharField(max_length=40, default="export_excel")
    object_type = models.CharField(max_length=60)
    object_id = models.PositiveBigIntegerField(null=True)
    department_ids = models.JSONField(default=list)
    status_code = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["-created_at"]
