from django.db import models


class Group(models.Model):
    class Meta:
        verbose_name = "Gruppe"
        verbose_name_plural = "Gruppen"

    name = models.CharField(max_length=200, default="", verbose_name="Gruppenname")
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Abteilung",
        related_name="groups",
    )

    def __str__(self):
        return self.name
