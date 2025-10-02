from django.db import models


class OrderStatus(models.Model):
    """Konfigurierbare Bestellstatus"""
    name = models.CharField(max_length=100, verbose_name="Status Name")
    code = models.CharField(max_length=20, unique=True, verbose_name="Status Code") 
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    color = models.CharField(max_length=7, default="#6c757d", help_text="Hex-Farbcode für die Anzeige", verbose_name="Farbe")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Sortierung")
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = "Bestellstatus"
        verbose_name_plural = "Bestellstatus"
    
    def __str__(self):
        return self.name
