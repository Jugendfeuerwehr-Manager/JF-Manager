from django.db import models
from users.models import CustomUser
from .order_status import OrderStatus


class OrderItemStatusHistory(models.Model):
    """History of status changes for order items"""
    order_item = models.ForeignKey(
        'OrderItem',
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name="Bestellartikel"
    )
    from_status = models.ForeignKey(
        OrderStatus,
        on_delete=models.PROTECT,
        related_name='status_history_from',
        null=True,
        blank=True,
        verbose_name="Von Status"
    )
    to_status = models.ForeignKey(
        OrderStatus,
        on_delete=models.PROTECT,
        related_name='status_history_to',
        verbose_name="Zu Status"
    )
    changed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Geändert von"
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Geändert am")
    notes = models.TextField(blank=True, verbose_name="Bemerkungen")
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name = "Status-Änderung"
        verbose_name_plural = "Status-Änderungen"
    
    def __str__(self):
        from_str = self.from_status.name if self.from_status else "Neu"
        return f"{self.order_item} - {from_str} → {self.to_status.name}"
