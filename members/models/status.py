from django.db import models
from colorfield.fields import ColorField

class Status(models.Model):

    class Meta:
        verbose_name = "Status"
        verbose_name_plural = "Status"

    name = models.CharField(max_length=200, default='', verbose_name="Mitgliedschaftsstatus")
    color = ColorField(default='#FF0000')

    def __str__(self):
        return self.name
