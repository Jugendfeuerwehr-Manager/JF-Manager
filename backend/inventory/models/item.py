from django.db import models
from django.urls import reverse
from members.models.member import Member
from .category import Category


class Item(models.Model):
    """Inventar-Artikel (Hauptartikel ohne Varianten-spezifische Daten)"""
    name = models.CharField(max_length=200, blank=True, default='', verbose_name='Name')
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,  # nullable für bestehende Daten
        verbose_name='Kategorie'
    )
    base_unit = models.CharField(
        max_length=50,
        default='Stück',
        verbose_name='Grundeinheit'
    )
    attributes = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Basis-Attribute',
        help_text='Grundlegende Attribute des Artikels (z.B. {"marke": "Adidas", "typ": "Hose"})'
    )
    is_variant_parent = models.BooleanField(
        default=False,
        verbose_name='Hat Varianten',
        help_text='Markieren Sie dies, wenn dieser Artikel Varianten hat (z.B. verschiedene Größen)'
    )

    # Legacy Felder
    size = models.CharField(max_length=100, blank=True, default='', verbose_name='Größe ')
    identifier1 = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Inventarnummer Hand'
    )
    identifier2 = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Inventarnummer Barcode'
    )
    rented_by = models.ForeignKey(
        Member,
        blank=True,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Ausgeliehen von'
    )

    class Meta:
        verbose_name = 'Artikel'
        verbose_name_plural = 'Artikel'
        ordering = ['name']
        permissions = [
            ('can_rent', 'can rent items to members'),
        ]

    def __str__(self):
        if self.name:
            return self.name
        elif self.category and self.size:
            return f"{self.category.name} gr. {self.size}"
        return f"Item #{self.pk}"

    def get_absolute_url(self):
        return reverse('inventory:item_detail', kwargs={'pk': self.pk})

    @property
    def total_stock(self):
        if self.is_variant_parent:
            total = 0
            for variant in self.variants.all():
                total += variant.total_stock
            return total
        return self.stock_set.aggregate(total=models.Sum('quantity'))['total'] or 0

    def get_variants(self):
        if self.is_variant_parent:
            return self.variants.all()
        return self.itemvariant_set.none()

    def get_display_name(self):
        if self.is_variant_parent:
            return f"{self.name} (Verschiedene Varianten)"
        return str(self)
