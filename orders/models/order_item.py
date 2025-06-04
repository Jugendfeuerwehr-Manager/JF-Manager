from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from .order_status import OrderStatus
from .orderable_item import OrderableItem
from .order import Order


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
    
    def clean(self):
        """Validate status transitions using workflow rules"""
        super().clean()
        
        if self.pk:  # Only validate for existing instances
            try:
                original = OrderItem.objects.get(pk=self.pk)
                if original.status != self.status:
                    # Check if status transition is allowed
                    from ..notifications import OrderWorkflowService
                    if not OrderWorkflowService.can_transition_to(original.status, self.status):
                        raise ValidationError(
                            f'Status transition from "{original.status.name}" to "{self.status.name}" is not allowed.'
                        )
            except OrderItem.DoesNotExist:
                pass  # New instance, no validation needed
    
    def save(self, *args, **kwargs):
        """Override save to automatically track status changes"""
        # Get the user from kwargs if provided (for tracking who made the change)
        changed_by = kwargs.pop('changed_by', None)
        notes = kwargs.pop('status_change_notes', '')
        
        # Check if this is an update and status has changed
        old_status = None
        if self.pk:
            try:
                original = OrderItem.objects.get(pk=self.pk)
                if original.status != self.status:
                    old_status = original.status
                    
                    # Auto-update dates based on status
                    if self.status.code == 'received' and not self.received_date:
                        self.received_date = timezone.now()
                    elif self.status.code == 'delivered' and not self.delivered_date:
                        self.delivered_date = timezone.now()
                        
            except OrderItem.DoesNotExist:
                pass  # New instance
        
        # Save the model first
        super().save(*args, **kwargs)
        
        # Create status history entry if status changed
        if old_status and old_status != self.status:
            # Use string reference to avoid circular imports
            from django.apps import apps
            OrderItemStatusHistory = apps.get_model('orders', 'OrderItemStatusHistory')
            OrderItemStatusHistory.objects.create(
                order_item=self,
                from_status=old_status,
                to_status=self.status,
                changed_by=changed_by,
                notes=notes or f"Status changed from {old_status.name} to {self.status.name}"
            )
    
    def get_available_next_statuses(self):
        """Get list of statuses this item can transition to"""
        from ..notifications import OrderWorkflowService
        return OrderWorkflowService.get_next_statuses(self.status)
    
    def can_transition_to_status(self, target_status):
        """Check if this item can transition to the given status"""
        from ..notifications import OrderWorkflowService
        return OrderWorkflowService.can_transition_to(self.status, target_status)
