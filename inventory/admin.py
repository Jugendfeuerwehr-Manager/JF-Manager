from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Category, Item

# Register your models here.
@admin.register(Category)
class DivisionAdmin(admin.ModelAdmin):
    search_fields = ['name']
    ordering = ['name']

@admin.register(Item)
class DivisionAdmin(admin.ModelAdmin):
    search_fields = ['category',' identifier1', 'identifier2']
    list_display = ('category', 'identifier1', 'identifier2')
    autocomplete_fields = ['rented_by', 'category']

