from django.db import models

class Category(models.Model):
    """Kategorie für Inventar-Artikel"""
    name = models.CharField(max_length=100, verbose_name='Name')
    schema = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Schema',
        help_text='Variable Attribute pro Kategorie (z.B. {"größe": "string", "farbe": "string"})'
    )

    class Meta:
        verbose_name = 'Kategorie'
        verbose_name_plural = 'Kategorien'
        ordering = ['name']

    def __str__(self):
        return self.name
