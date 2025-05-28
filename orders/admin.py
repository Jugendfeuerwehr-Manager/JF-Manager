from django.contrib import admin
from .models import OrderStatus, OrderableItem, Order, OrderItem, OrderItemStatusHistory


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
