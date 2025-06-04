from django.db import models


class OrderableItem(models.Model):
    """Bestellbare Ausrüstungsgegenstände"""
    name = models.CharField(max_length=200, verbose_name="Name")
    category = models.CharField(max_length=100, verbose_name="Kategorie")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    has_sizes = models.BooleanField(default=True, verbose_name="Hat Größen")
    available_sizes = models.TextField(
        blank=True, 
        verbose_name="Verfügbare Größen",
        help_text="Größen kommagetrennt eingeben, z.B.: XS,S,M,L,XL oder 98,104,110,116"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Bestellbarer Artikel"
        verbose_name_plural = "Bestellbare Artikel"
    
    def __str__(self):
        return f"{self.category} - {self.name}"
    
    def get_sizes_list(self):
        """Gibt die verfügbaren Größen als Liste zurück"""
        if not self.available_sizes:
            return []
        return [size.strip() for size in self.available_sizes.split(',')]
