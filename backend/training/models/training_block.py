from django.db import models


class TrainingBlock(models.Model):
    """
    A block within a training session. Assigned to one or more groups
    (empty M2M = block applies to ALL groups — rendered full-width in swimlane).
    May be instantiated from a LibraryBlock.
    """

    class Meta:
        verbose_name = "Trainingsblock"
        verbose_name_plural = "Trainingsblöcke"
        ordering = ['session', 'start_offset_minutes', 'position_order']

    title = models.CharField(max_length=300, verbose_name="Titel")

    # Rich-text content (HTML from Tiptap) — may be copied from library_block on creation
    content = models.TextField(blank=True, verbose_name="Inhalt (HTML)")

    session = models.ForeignKey(
        'training.TrainingSession',
        on_delete=models.CASCADE,
        related_name='blocks',
        verbose_name="Trainingseinheit",
    )
    groups = models.ManyToManyField(
        'members.Group',
        blank=True,
        related_name='training_blocks',
        verbose_name="Gruppen",
        help_text="Leerlassen = Block gilt für alle Gruppen (Full-Width Swimlane)",
    )

    # Optional link to source library block (keeps reference for re-use)
    library_block = models.ForeignKey(
        'training.LibraryBlock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_blocks',
        verbose_name="Bibliotheksblock (Vorlage)",
    )

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} @ {self.session}"
