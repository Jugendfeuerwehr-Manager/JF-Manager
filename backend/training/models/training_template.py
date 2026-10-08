from django.db import models

from .training_block import PlanBlockFields


class TrainingTemplate(models.Model):
    """A whole exercise saved for reuse. It owns independent copies of all
    block content, images and attachments, so later changes or deletions of the
    source exercise or library never alter the template or exercises made from it."""

    class Meta:
        verbose_name = "Übungsvorlage"
        verbose_name_plural = "Übungsvorlagen"
        ordering = ["title", "pk"]

    title = models.CharField(max_length=300, verbose_name="Titel")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    start_time = models.TimeField(verbose_name="Beginn")
    end_time = models.TimeField(verbose_name="Ende")
    location = models.CharField(max_length=300, blank=True, verbose_name="Ort")
    notes = models.TextField(blank=True, verbose_name="Notizen")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_templates",
        verbose_name="Abteilung",
    )
    groups = models.ManyToManyField(
        "members.Group", blank=True, related_name="training_templates", verbose_name="Gruppen"
    )
    source_session = models.ForeignKey(
        "training.TrainingSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_templates",
        verbose_name="Ursprüngliche Übung",
    )
    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_training_templates",
        verbose_name="Erstellt von",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class TrainingTemplateBlock(PlanBlockFields):
    class Meta:
        verbose_name = "Vorlagenbaustein"
        verbose_name_plural = "Vorlagenbausteine"
        ordering = ["template", "start_offset_minutes", "position_order", "pk"]

    template = models.ForeignKey(TrainingTemplate, on_delete=models.CASCADE, related_name="blocks")
    groups = models.ManyToManyField(
        "members.Group", blank=True, related_name="training_template_blocks", verbose_name="Gruppen"
    )
    library_block = models.ForeignKey(
        "training.LibraryBlock",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="template_blocks",
        verbose_name="Bibliotheksblock (Herkunft)",
    )
    instructors = models.ManyToManyField(
        "users.CustomUser", blank=True, related_name="instructed_training_template_blocks", verbose_name="Ausbilder"
    )

    def __str__(self):
        return f"{self.title} @ {self.template}"
