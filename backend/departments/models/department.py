from django.db import models
from django.utils.text import slugify


class Department(models.Model):
    """
    Represents a sub-organisation / district station within the youth fire brigade.
    Members, inventory, orders, services and training sessions can all be scoped
    to a Department.  Records with department=NULL are treated as "central" items
    that are visible to users of every department.
    """

    name = models.CharField(max_length=200, verbose_name="Name")
    code = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name="Kürzel",
        help_text="Eindeutiges Kürzel für die Abteilung (wird automatisch aus dem Namen generiert)",
    )
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    address = models.CharField(max_length=300, blank=True, verbose_name="Adresse")
    phone = models.CharField(max_length=50, blank=True, verbose_name="Telefon")
    color = models.CharField(
        max_length=7,
        default="#2563EB",
        verbose_name="Farbe",
        help_text="Hex-Farbe zur visuellen Kennzeichnung (z.B. #2563EB)",
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Abteilung"
        verbose_name_plural = "Abteilungen"
        ordering = ["name"]
        permissions = (
            ("can_access_all_departments", "Kann alle Abteilungen sehen"),
            ("can_manage_all_departments", "Kann alle Abteilungen verwalten"),
        )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = slugify(self.name)
        super().save(*args, **kwargs)
