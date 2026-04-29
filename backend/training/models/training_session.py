from django.conf import settings
from django.db import models


class TrainingSession(models.Model):
    """
    A single training event. Multiple groups train at the same time.
    May be part of a recurring series (series_parent FK).
    """

    class Meta:
        verbose_name = "Trainingseinheit"
        verbose_name_plural = "Trainingseinheiten"
        ordering = ['-date', 'start_time']

    class RecurrenceFrequency(models.TextChoices):
        WEEKLY = 'WEEKLY', 'Wöchentlich'
        BIWEEKLY = 'BIWEEKLY', 'Zweiwöchentlich'
        MONTHLY = 'MONTHLY', 'Monatlich'

    title = models.CharField(max_length=300, verbose_name="Titel")
    description = models.TextField(blank=True, verbose_name="Beschreibung")

    date = models.DateField(verbose_name="Datum")
    start_time = models.TimeField(verbose_name="Beginn")
    end_time = models.TimeField(verbose_name="Ende")
    location = models.CharField(max_length=300, blank=True, verbose_name="Ort")
    notes = models.TextField(blank=True, verbose_name="Notizen")

    groups = models.ManyToManyField(
        'members.Group',
        blank=True,
        related_name='training_sessions',
        verbose_name="Gruppen",
        help_text="Leerlassen = Alle Gruppen",
    )

    # Recurrence support
    series_parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='series_children',
        verbose_name="Serienvorlage",
    )
    recurrence_rule = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Wiederholungsregel",
        help_text='{"frequency": "WEEKLY|BIWEEKLY|MONTHLY", "end_date": "YYYY-MM-DD"}',
    )

    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_training_sessions',
        verbose_name="Erstellt von",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def duration_minutes(self):
        """Total session duration in minutes."""
        from datetime import datetime, date
        start = datetime.combine(date.today(), self.start_time)
        end = datetime.combine(date.today(), self.end_time)
        return int((end - start).total_seconds() / 60)
