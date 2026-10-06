from django.db import models


class BlockKind(models.TextChoices):
    BLOCK = "block", "Baustein"
    STATION = "station", "Station"
    TRANSITION = "transition", "Wechsel"
    BREAK = "break", "Pause"
    FREE = "free", "Freie Runde"


class PlanBlockFields(models.Model):
    """Content shared by planned blocks and exercise-template blocks.
    For stations, ``content`` is the procedure and ``duration_minutes`` the station time."""

    class Meta:
        abstract = True

    kind = models.CharField(max_length=12, choices=BlockKind.choices, default=BlockKind.BLOCK, verbose_name="Art")
    location = models.CharField(max_length=300, blank=True, verbose_name="Ort")
    learning_objective = models.TextField(blank=True, verbose_name="Lernziel")
    safety_notes = models.TextField(blank=True, verbose_name="Sicherheitshinweise")

    title = models.CharField(max_length=300, verbose_name="Titel")

    # Rich-text content (HTML from Tiptap) — may be copied from library_block on creation
    content = models.TextField(blank=True, verbose_name="Inhalt (HTML)")

    # Planner positioning
    duration_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name="Dauer (Minuten)",
    )
    start_offset_minutes = models.IntegerField(
        default=0,
        verbose_name="Start-Offset (Minuten vom Beginn der Einheit)",
    )
    position_order = models.IntegerField(
        default=0,
        verbose_name="Position (für Sortierung auf gleicher Zeitachse)",
    )

    color = models.CharField(max_length=20, blank=True, verbose_name="Farbe (Hex)")
    nextcloud_folder_url = models.URLField(
        blank=True,
        verbose_name="Nextcloud-Ordner URL",
    )


class TrainingBlock(PlanBlockFields):
    """
    A block within a training session. Assigned to one or more groups
    (empty M2M = block applies to ALL groups — rendered full-width in swimlane).
    May be instantiated from a LibraryBlock.
    """

    class Meta:
        verbose_name = "Trainingsblock"
        verbose_name_plural = "Trainingsblöcke"
        ordering = ["session", "start_offset_minutes", "position_order"]

    session = models.ForeignKey(
        "training.TrainingSession",
        on_delete=models.CASCADE,
        related_name="blocks",
        verbose_name="Trainingseinheit",
    )
    groups = models.ManyToManyField(
        "members.Group",
        blank=True,
        related_name="training_blocks",
        verbose_name="Gruppen",
        help_text="Leerlassen = Block gilt für alle Gruppen (Full-Width Swimlane)",
    )

    # Optional link to source library block (keeps reference for re-use)
    library_block = models.ForeignKey(
        "training.LibraryBlock",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_blocks",
        verbose_name="Bibliotheksblock (Vorlage)",
    )

    instructors = models.ManyToManyField(
        "users.CustomUser", blank=True, related_name="instructed_training_blocks", verbose_name="Ausbilder"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} @ {self.session}"


class TrainingBlockMaterial(models.Model):
    """Planned material need. It never books or reserves stock (TRAIN-02)."""

    class Meta:
        verbose_name = "Materialbedarf"
        verbose_name_plural = "Materialbedarfe"
        ordering = ["pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(block__isnull=False, template_block__isnull=True)
                | models.Q(block__isnull=True, template_block__isnull=False),
                name="training_material_single_owner",
            ),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="training_material_positive_quantity"),
        ]

    block = models.ForeignKey(TrainingBlock, on_delete=models.CASCADE, null=True, blank=True, related_name="materials")
    template_block = models.ForeignKey(
        "training.TrainingTemplateBlock", on_delete=models.CASCADE, null=True, blank=True, related_name="materials"
    )
    item = models.ForeignKey(
        "inventory.Item", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Artikel"
    )
    variant = models.ForeignKey(
        "inventory.ItemVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Variante",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Menge")
    # Kept as display name, also after an inventory item was removed.
    label = models.CharField(max_length=200, blank=True, verbose_name="Bezeichnung")

    def __str__(self):
        return f"{self.quantity} × {self.label}"
