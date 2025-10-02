from django.contrib import admin

from .models import Category, Item, ItemVariant, StorageLocation, Stock, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'schema')
    search_fields = ['name']
    ordering = ['name']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'base_unit', 'total_stock', 'identifier1', 'identifier2')
    list_filter = ('category', 'base_unit')
    search_fields = ['name', 'identifier1', 'identifier2']
    autocomplete_fields = ['rented_by', 'category']
    readonly_fields = ('total_stock',)
    
    fieldsets = (
        ('Grunddaten', {
            'fields': ('name', 'category', 'base_unit', 'attributes')
        }),
        ('Inventarnummern', {
            'fields': ('identifier1', 'identifier2')
        }),
        ('Legacy', {
            'fields': ('size', 'rented_by'),
            'classes': ('collapse',)
        }),
        ('Statistiken', {
            'fields': ('total_stock',),
            'classes': ('collapse',)
        })
    )

@admin.register(ItemVariant)
class ItemVariantAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'parent_item', 'sku', 'total_stock')
    search_fields = ['sku', 'parent_item__name']
    autocomplete_fields = ['parent_item']
    readonly_fields = ('total_stock',)
    list_filter = ('parent_item__category',)
    fieldsets = (
        ('Variante', {
            'fields': ('parent_item', 'sku', 'variant_attributes')
        }),
        ('Statistiken', {
            'fields': ('total_stock',),
            'classes': ('collapse',)
        })
    )

    def total_stock(self, obj):  # type: ignore
        return obj.total_stock
    total_stock.short_description = 'Bestand'


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_member', 'member')
    list_filter = ('is_member',)
    search_fields = ['name', 'member__name', 'member__lastname']
    autocomplete_fields = ['member']


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('item', 'location', 'quantity')
    list_filter = ('location', 'item__category')
    search_fields = ['item__name', 'location__name']
    autocomplete_fields = ['item', 'location']
    readonly_fields = ('item', 'location')  # Prevent direct editing
    
    def has_add_permission(self, request):
        return False  # Stock wird nur über Transaktionen erstellt
    
    def has_change_permission(self, request, obj=None):
        return False  # Stock wird nur über Transaktionen geändert


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'transaction_type', 'item', 'quantity', 'source', 'target', 'user')
    list_filter = ('transaction_type', 'date', 'item__category')
    search_fields = ['item__name', 'source__name', 'target__name', 'note']
    autocomplete_fields = ['item', 'source', 'target', 'user']
    readonly_fields = ('date',)
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Transaktion', {
            'fields': ('transaction_type', 'item', 'quantity', 'date')
        }),
        ('Bewegung', {
            'fields': ('source', 'target')
        }),
        ('Details', {
            'fields': ('user', 'note')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)

