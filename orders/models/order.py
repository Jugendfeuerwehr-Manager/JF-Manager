from django.db import models
from django.urls import reverse
from members.models import Member
from users.models import CustomUser


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
