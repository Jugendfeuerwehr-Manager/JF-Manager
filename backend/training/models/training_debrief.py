from django.conf import settings
from django.db import models


class TrainingDebrief(models.Model):
    """Follow-up of a held exercise (TRAIN-04).

    Actual times are kept apart from the planned ones; attendance stays in the
    servicebook. Its own revision prevents silent overwrites. Copies, series
    and templates never carry it.
    """

    session = models.OneToOneField(
        "training.TrainingSession", on_delete=models.CASCADE, related_name="debrief", verbose_name="Übung"
    )
    actual_start = models.TimeField(null=True, blank=True, verbose_name="Tatsächlicher Beginn")
    actual_end = models.TimeField(null=True, blank=True, verbose_name="Tatsächliches Ende")
    reflection = models.TextField(blank=True, verbose_name="Reflexion")
    improvements = models.TextField(blank=True, verbose_name="Verbesserungshinweise")
    revision = models.PositiveIntegerField(default=0, editable=False, verbose_name="Version")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", editable=False
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Nachbereitung"
        verbose_name_plural = "Nachbereitungen"

    def __str__(self):
        return f"Nachbereitung {self.session}"

    @property
    def actual_minutes(self):
        if self.actual_start is None or self.actual_end is None:
            return None
        return (self.actual_end.hour * 60 + self.actual_end.minute) - (
            self.actual_start.hour * 60 + self.actual_start.minute
        )
