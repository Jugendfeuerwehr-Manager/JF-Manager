from django.db import models

class Group(models.Model):

    class Meta:
        verbose_name = "Gruppe"
        verbose_name_plural = "Gruppen"

    name = models.CharField(max_length=200, default='', verbose_name="Gruppenname")

    def __str__(self):
        return self.name
