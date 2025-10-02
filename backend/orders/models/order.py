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
    
    def get_common_status(self):
        """Gibt den am häufigsten vorkommenden Status der Artikel zurück"""
        from collections import Counter
        if not self.items.exists():
            return None
        statuses = [item.status for item in self.items.all() if item.status]
        if not statuses:
            return None
        counter = Counter(statuses)
        return counter.most_common(1)[0][0]
    
    def get_next_status_options(self):
        """Gibt die nächsten möglichen Status für die Bestellung zurück"""
        from .order_status import OrderStatus
        current_status = self.get_common_status()
        if not current_status:
            return OrderStatus.objects.filter(is_active=True)[:3]
        
        # Hole die nächsten 2-3 Status nach sort_order
        next_statuses = OrderStatus.objects.filter(
            is_active=True,
            sort_order__gt=current_status.sort_order
        ).order_by('sort_order')[:3]
        
        return next_statuses
