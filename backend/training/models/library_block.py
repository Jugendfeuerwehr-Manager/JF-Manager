import uuid

from django.db import models


class LibraryBlockCategory(models.Model):
    """Category for grouping library blocks (e.g. Game, Education, Safety)."""

    class Meta:
        verbose_name = "Bibliotheksblock-Kategorie"
        verbose_name_plural = "Bibliotheksblock-Kategorien"
        ordering = ["name"]

    name = models.CharField(max_length=200, verbose_name="Name")
    color = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Farbe (Hex)",
        help_text="z.B. #3B82F6",
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Icon (PrimeVue icon name)",
        help_text="z.B. pi pi-star",
    )

    def __str__(self):
        return self.name


class LibraryBlockTag(models.Model):
    """Simple tag for library blocks."""

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]

    name = models.CharField(max_length=100, unique=True, verbose_name="Name")

    def __str__(self):
        return self.name


class LibraryBlock(models.Model):
    """
    A reusable training block that can be placed into any training session.
    Can be exported/imported across JF-Manager instances using export_uuid.
    """

    class Meta:
        verbose_name = "Bibliotheksblock"
        verbose_name_plural = "Bibliotheksblöcke"
        ordering = ["title"]

    # Federation identity — survives export/import
    export_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Export-UUID",
    )

    title = models.CharField(max_length=300, verbose_name="Titel")
    description = models.TextField(blank=True, verbose_name="Kurzbeschreibung")

    # Rich-text content (HTML from Tiptap)
    content = models.TextField(blank=True, verbose_name="Inhalt (HTML)")

    default_duration_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name="Standard-Dauer (Minuten)",
    )

    category = models.ForeignKey(
        LibraryBlockCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocks",
        verbose_name="Kategorie",
    )
    tags = models.ManyToManyField(
        LibraryBlockTag,
        blank=True,
        related_name="blocks",
        verbose_name="Tags",
    )

    color = models.CharField(max_length=20, blank=True, verbose_name="Farbe (Hex)")
    nextcloud_folder_url = models.URLField(
        blank=True,
        verbose_name="Nextcloud-Ordner URL",
    )

    is_public = models.BooleanField(
        default=False,
        verbose_name="Öffentlich",
        help_text="Für zukünftige Bibliotheks-Freigabe",
    )
    source_instance_url = models.URLField(
        blank=True,
        verbose_name="Import-Quelle (URL)",
        help_text="Gesetzt wenn der Block aus einer anderen Instanz importiert wurde",
    )

    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_library_blocks",
        verbose_name="Erstellt von",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
