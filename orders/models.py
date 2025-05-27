from django.db import models
from django.urls import reverse
from members.models import Member
from users.models import CustomUser


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


class Order(models.Model):
    """Hauptbestellung"""
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        verbose_name="Mitglied"
    )
    ordered_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Bestellt von"
    )
    order_date = models.DateTimeField(auto_now_add=True, verbose_name="Bestelldatum")
    notes = models.TextField(blank=True, verbose_name="Bemerkungen")
    
    class Meta:
        ordering = ['-order_date']
        verbose_name = "Bestellung"
        verbose_name_plural = "Bestellungen"
        permissions = (
            ("can_manage_orders", "Kann Bestellungen verwalten"),
            ("can_change_order_status", "Kann Bestellstatus ändern"),
        )
    
    def __str__(self):
        return f"Bestellung #{self.pk} für {self.member}"
    
    def get_absolute_url(self):
        return reverse('orders:detail', kwargs={'pk': self.pk})


class OrderItem(models.Model):
    """Einzelne Artikel in einer Bestellung"""
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="Bestellung"
    )
    item = models.ForeignKey(
        OrderableItem, 
        on_delete=models.CASCADE,
        verbose_name="Artikel"
    )
    size = models.CharField(max_length=50, blank=True, verbose_name="Größe")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Anzahl")
    status = models.ForeignKey(
        OrderStatus,
        on_delete=models.PROTECT,
        verbose_name="Status"
    )
    received_date = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Eingangsdatum"
    )
    delivered_date = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Ausgabedatum"
    )
    notes = models.TextField(blank=True, verbose_name="Bemerkungen")
    
    class Meta:
        verbose_name = "Bestellartikel"
        verbose_name_plural = "Bestellartikel"
    
    def __str__(self):
        size_info = f" (Größe: {self.size})" if self.size else ""
        return f"{self.item.name}{size_info} - {self.status.name}"
