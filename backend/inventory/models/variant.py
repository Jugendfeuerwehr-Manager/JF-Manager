from django.db import models
from django.urls import reverse
from .item import Item


class ItemVariant(models.Model):
    """Artikel-Variante (z.B. Hose Gr. 164, Hose Gr. 176)"""
    parent_item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Hauptartikel'
    )
    variant_attributes = models.JSONField(
        verbose_name='Varianten-Attribute',
        help_text='Spezifische Attribute dieser Variante (z.B. {"größe": "164", "farbe": "blau"})'
    )
    sku = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='SKU/Artikelnummer',
        help_text='Eindeutige Artikelnummer für diese Variante'
    )

    class Meta:
        verbose_name = 'Artikel-Variante'
        verbose_name_plural = 'Artikel-Varianten'
        unique_together = ['parent_item', 'variant_attributes']
        ordering = ['parent_item__name', 'sku']

    def __str__(self):
        variant_parts = []
        if self.variant_attributes:
            for key, value in self.variant_attributes.items():
                variant_parts.append(f"{key}: {value}")
        if variant_parts:
            return f"{self.parent_item.name} ({', '.join(variant_parts)})"
        return f"{self.parent_item.name} (Variante #{self.pk})"

    @property
    def name(self):
        return str(self)

    @property
    def category(self):
        return self.parent_item.category

    @property
    def total_stock(self):
        return self.stock_set.aggregate(total=models.Sum('quantity'))['total'] or 0

    def get_absolute_url(self):
        return reverse('inventory:variant_detail', kwargs={'pk': self.pk})

    def get_combined_attributes(self):
        combined = {}
        if self.parent_item.attributes:
            combined.update(self.parent_item.attributes)
        if self.variant_attributes:
            combined.update(self.variant_attributes)
        return combined
