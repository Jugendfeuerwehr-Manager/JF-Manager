from django.contrib import admin
from .models import (
    OrderStatus, OrderableItem, Order, OrderItem, OrderItemStatusHistory,
    NotificationPreference, NotificationLog, EmailTemplate
)


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'sort_order']
    list_editable = ['is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['sort_order', 'name']


@admin.register(OrderableItem)
class OrderableItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'has_sizes', 'is_active', 'created_at']
    list_editable = ['is_active']
    list_filter = ['category', 'has_sizes', 'is_active']
    search_fields = ['name', 'category', 'description']
    ordering = ['category', 'name']
    
    fieldsets = (
        ('Grunddaten', {
            'fields': ('name', 'category', 'description', 'is_active')
        }),
        ('Größen', {
            'fields': ('has_sizes', 'available_sizes'),
            'description': 'Größen kommagetrennt eingeben, z.B.: XS,S,M,L,XL'
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['item', 'size', 'quantity', 'status', 'notes']
    autocomplete_fields = ['item']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'member', 'ordered_by', 'order_date', 'get_items_count']
    list_filter = ['order_date', 'ordered_by']
    search_fields = ['member__name', 'member__lastname', 'ordered_by__username']
    autocomplete_fields = ['member', 'ordered_by']
    inlines = [OrderItemInline]
    readonly_fields = ['order_date']
    
    def get_items_count(self, obj):
        return obj.items.count()
    get_items_count.short_description = 'Anzahl Artikel'
    
    fieldsets = (
        ('Bestellung', {
            'fields': ('member', 'ordered_by', 'order_date')
        }),
        ('Bemerkungen', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

class OrderItemStatusHistoryInline(admin.TabularInline):
    model = OrderItemStatusHistory
    extra = 0
    fields = ['from_status', 'to_status', 'changed_by', 'changed_at', 'notes']
    readonly_fields = ['changed_at']
    ordering = ['-changed_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'order', 'item', 'size', 'quantity', 'status', 'received_date', 'delivered_date']
    list_filter = ['status', 'received_date', 'delivered_date', 'item__category']
    search_fields = ['order__member__name', 'order__member__lastname', 'item__name']
    autocomplete_fields = ['order', 'item', 'status']
    list_editable = ['status']
    inlines = [OrderItemStatusHistoryInline]
    
    fieldsets = (
        ('Artikel', {
            'fields': ('order', 'item', 'size', 'quantity')
        }),
        ('Status', {
            'fields': ('status', 'received_date', 'delivered_date')
        }),
        ('Bemerkungen', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Override save to track status changes"""
        if change:
            # Get the original instance to compare status
            original = OrderItem.objects.get(pk=obj.pk)
            if original.status != obj.status:
                # Create status history entry
                OrderItemStatusHistory.objects.create(
                    order_item=obj,
                    from_status=original.status,
                    to_status=obj.status,
                    changed_by=request.user,
                    notes=f"Status changed via admin interface"
                )
        
        super().save_model(request, obj, form, change)





@admin.register(OrderItemStatusHistory)
class OrderItemStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order_item', 'from_status', 'to_status', 'changed_by', 'changed_at']
    list_filter = ['from_status', 'to_status', 'changed_at', 'changed_by']
    search_fields = ['order_item__order__member__name', 'order_item__order__member__lastname', 'order_item__item__name']
    readonly_fields = ['changed_at']
    autocomplete_fields = ['order_item', 'from_status', 'to_status', 'changed_by']
    
    fieldsets = (
        ('Status-Änderung', {
            'fields': ('order_item', 'from_status', 'to_status', 'changed_by', 'changed_at')
        }),
        ('Bemerkungen', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


# Notification Admin Classes
@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_new_orders', 'email_status_updates', 'email_bulk_updates', 'email_pending_reminders']
    list_filter = ['email_new_orders', 'email_status_updates', 'email_bulk_updates', 'email_pending_reminders']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email']
    autocomplete_fields = ['user']
    
    fieldsets = (
        ('Benutzer', {
            'fields': ('user',)
        }),
        ('E-Mail Benachrichtigungen', {
            'fields': ('email_new_orders', 'email_status_updates', 'email_bulk_updates', 'email_pending_reminders')
        }),
        ('Admin Benachrichtigungen', {
            'fields': ('email_daily_summary', 'email_weekly_report'),
            'classes': ('collapse',)
        }),
        ('Einstellungen', {
            'fields': ('reminder_frequency_days',),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['notification_type', 'recipient_email', 'status', 'sent_at', 'created_at']
    list_filter = ['notification_type', 'status', 'sent_at', 'created_at']
    search_fields = ['recipient_email', 'subject', 'order__pk', 'order_item__item__name']
    readonly_fields = ['notification_type', 'recipient_email', 'subject', 'status', 'order', 'order_item', 'sent_at', 'error_message', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Benachrichtigung', {
            'fields': ('notification_type', 'recipient_email', 'subject', 'status')
        }),
        ('Verknüpfte Objekte', {
            'fields': ('order', 'order_item'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('sent_at', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Zeitstempel', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Logs should not be manually created
    
    def has_change_permission(self, request, obj=None):
        return False  # Logs should not be edited
    
    actions = ['mark_as_sent', 'mark_as_failed']
    
    def mark_as_sent(self, request, queryset):
        updated = 0
        for log in queryset.filter(status='pending'):
            log.mark_as_sent()
            updated += 1
        self.message_user(request, f'{updated} Benachrichtigungen wurden als gesendet markiert.')
    mark_as_sent.short_description = "Als gesendet markieren"
    
    def mark_as_failed(self, request, queryset):
        updated = 0
        for log in queryset.filter(status='pending'):
            log.mark_as_failed("Manuell als fehlgeschlagen markiert")
            updated += 1
        self.message_user(request, f'{updated} Benachrichtigungen wurden als fehlgeschlagen markiert.')
    mark_as_failed.short_description = "Als fehlgeschlagen markieren"


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'updated_at']
    list_filter = ['template_type', 'is_active', 'updated_at']
    search_fields = ['name', 'subject_template']
    actions = ['import_default_templates', 'send_order_summary']
    
    fieldsets = (
        ('Template Info', {
            'fields': ('name', 'template_type', 'is_active')
        }),
        ('Email Content', {
            'fields': ('subject_template', 'html_template', 'text_template')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ['template_type']
        return []
    
    def import_default_templates(self, request, queryset):
        """Import or reset default email templates"""
        from django.core.management import call_command
        from io import StringIO
        
        # Capture command output
        out = StringIO()
        try:
            call_command('create_default_email_templates', stdout=out)
            self.message_user(request, f"Standard-E-Mail-Templates erfolgreich importiert: {out.getvalue().strip()}")
        except Exception as e:
            self.message_user(request, f"Fehler beim Importieren der Standard-Templates: {str(e)}", level='error')
    
    import_default_templates.short_description = "Standard E-Mail-Templates importieren/zurücksetzen"
    
    def send_order_summary(self, request, queryset):
        """Send manual order summary to Gerätewart"""
        from django.contrib.auth.models import User
        from django.shortcuts import redirect
        from django.urls import reverse
        
        # Redirect to order summary form
        return redirect(reverse('orders:admin_send_order_summary'))
    
    send_order_summary.short_description = "Bestellübersicht an Gerätewart senden"
