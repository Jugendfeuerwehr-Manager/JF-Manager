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
    
    def clean(self):
        """Validate status transitions using workflow rules"""
        super().clean()
        
        if self.pk:  # Only validate for existing instances
            try:
                original = OrderItem.objects.get(pk=self.pk)
                if original.status != self.status:
                    # Check if status transition is allowed
                    from .notifications import OrderWorkflowService
                    if not OrderWorkflowService.can_transition_to(original.status, self.status):
                        from django.core.exceptions import ValidationError
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
                        from django.utils import timezone
                        self.received_date = timezone.now()
                    elif self.status.code == 'delivered' and not self.delivered_date:
                        from django.utils import timezone
                        self.delivered_date = timezone.now()
                        
            except OrderItem.DoesNotExist:
                pass  # New instance
        
        # Save the model first
        super().save(*args, **kwargs)
        
        # Create status history entry if status changed
        if old_status and old_status != self.status:
            OrderItemStatusHistory.objects.create(
                order_item=self,
                from_status=old_status,
                to_status=self.status,
                changed_by=changed_by,
                notes=notes or f"Status changed from {old_status.name} to {self.status.name}"
            )
    
    def get_available_next_statuses(self):
        """Get list of statuses this item can transition to"""
        from .notifications import OrderWorkflowService
        return OrderWorkflowService.get_next_statuses(self.status)
    
    def can_transition_to_status(self, target_status):
        """Check if this item can transition to the given status"""
        from .notifications import OrderWorkflowService
        return OrderWorkflowService.can_transition_to(self.status, target_status)
    

class OrderItemStatusHistory(models.Model):
    """History of status changes for order items"""
    order_item = models.ForeignKey(
        OrderItem,
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


# Notification Models
class NotificationPreference(models.Model):
    """User preferences for order notifications"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notification settings
    email_new_orders = models.BooleanField(default=True, verbose_name="Neue Bestellungen")
    email_status_updates = models.BooleanField(default=True, verbose_name="Status-Änderungen")
    email_bulk_updates = models.BooleanField(default=False, verbose_name="Massenänderungen")
    email_pending_reminders = models.BooleanField(default=False, verbose_name="Erinnerungen für offene Artikel")
    
    # Admin-only notifications
    email_daily_summary = models.BooleanField(default=False, verbose_name="Tägliche Zusammenfassung")
    email_weekly_report = models.BooleanField(default=False, verbose_name="Wöchentlicher Bericht")
    
    # Frequency settings
    reminder_frequency_days = models.PositiveIntegerField(default=7, verbose_name="Erinnerungs-Intervall (Tage)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Benachrichtigungseinstellung"
        verbose_name_plural = "Benachrichtigungseinstellungen"
    
    def __str__(self):
        return f"Einstellungen für {self.user.get_full_name()}"


class NotificationLog(models.Model):
    """Log of sent notifications for tracking and debugging"""
    NOTIFICATION_TYPES = [
        ('order_created', 'Bestellung erstellt'),
        ('status_update', 'Status geändert'),
        ('bulk_update', 'Massenänderung'),
        ('pending_reminder', 'Erinnerung'),
        ('daily_summary', 'Tägliche Zusammenfassung'),
        ('weekly_report', 'Wöchentlicher Bericht'),
        ('order_summary', 'Bestellübersicht für Gerätewart'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Gesendet'),
        ('failed', 'Fehlgeschlagen'),
        ('pending', 'Ausstehend'),
    ]
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name="Typ")
    recipient_email = models.EmailField(verbose_name="Empfänger")
    subject = models.CharField(max_length=255, verbose_name="Betreff")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    
    # Related objects
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bestellung")
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bestellartikel")
    
    # Metadata
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gesendet am")
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Benachrichtigungsprotokoll"
        verbose_name_plural = "Benachrichtigungsprotokolle"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} an {self.recipient_email} - {self.get_status_display()}"
    
    def mark_as_sent(self):
        """Mark notification as successfully sent"""
        from django.utils import timezone
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_message):
        """Mark notification as failed with error message"""
        self.status = 'failed'
        self.error_message = error_message
        self.save()


class EmailTemplate(models.Model):
    """Customizable email templates"""
    TEMPLATE_TYPES = [
        ('order_created', 'Bestellung erstellt'),
        ('status_update', 'Status geändert'),
        ('bulk_update', 'Massenänderung'),
        ('pending_reminder', 'Erinnerung'),
        ('daily_summary', 'Tägliche Zusammenfassung'),
        ('weekly_report', 'Wöchentlicher Bericht'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Name")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, unique=True, verbose_name="Typ")
    subject_template = models.CharField(max_length=255, verbose_name="Betreff-Vorlage")
    html_template = models.TextField(verbose_name="HTML-Vorlage")
    text_template = models.TextField(blank=True, verbose_name="Text-Vorlage")
    
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "E-Mail-Vorlage"
        verbose_name_plural = "E-Mail-Vorlagen"
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
