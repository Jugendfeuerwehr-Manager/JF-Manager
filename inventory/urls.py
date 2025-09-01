from django.urls import path

from . import api_views
from .views import (
    ItemListView, ItemDetailView, ItemCreateView, ItemUpdateView, ItemDeleteView,
    StockListView,
    TransactionListView, TransactionCreateView, TransactionDetailView,
    MemberLoanListView,
    InventoryDashboardView,
    CategoryListView, CategoryDetailView, CategoryCreateView, CategoryUpdateView, CategoryDeleteView, CategoryBrowserView,
    StorageLocationListView, StorageLocationDetailView, StorageLocationCreateView, StorageLocationUpdateView, StorageLocationDeleteView,
    ItemVariantCreateView, ItemVariantDetailView,
    get_stock_info, get_filtered_locations, search_items, search_locations,
)


app_name = 'inventory'
urlpatterns = [
    # Dashboard
    path('', InventoryDashboardView.as_view(), name='dashboard'),
    
    # Artikel URLs
    path('items/', ItemListView.as_view(), name='item_list'),
    path('items/', ItemListView.as_view(), name='items'),  # Alias für Navigation
    path('items/<int:pk>/', ItemDetailView.as_view(), name='item_detail'),
    path('items/new/', ItemCreateView.as_view(), name='item_create'),
    path('items/<int:pk>/edit/', ItemUpdateView.as_view(), name='item_edit'),
    path('items/<int:pk>/delete/', ItemDeleteView.as_view(), name='item_delete'),
    
    # Varianten URLs
    path('variants/<int:pk>/', ItemVariantDetailView.as_view(), name='variant_detail'),
    path('variants/new/', ItemVariantCreateView.as_view(), name='variant_create'),
    
    # Bestände URLs
    path('stocks/', StockListView.as_view(), name='stock_list'),
    
    # Transaktionen URLs
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('transactions/new/', TransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),
    
    # Mitglieder-Ausleihen URLs
    path('loans/', MemberLoanListView.as_view(), name='member_loans'),
    
    # Kategorien URLs
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/browser/', CategoryBrowserView.as_view(), name='category_browser'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),
    path('categories/new/', CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),
    
    # Lagerorte URLs
    path('locations/', StorageLocationListView.as_view(), name='location_list'),
    path('locations/<int:pk>/', StorageLocationDetailView.as_view(), name='location_detail'),
    path('locations/new/', StorageLocationCreateView.as_view(), name='location_create'),
    path('locations/<int:pk>/edit/', StorageLocationUpdateView.as_view(), name='location_edit'),
    path('locations/<int:pk>/delete/', StorageLocationDeleteView.as_view(), name='location_delete'),
    
    # API-URLs für AJAX-Anfragen
    path('api/search/items/', api_views.search_items, name='api_search_items'),
    path('api/search/items-and-variants/', api_views.search_items_and_variants, name='api_search_items_and_variants'),
    path('api/search/locations/', api_views.search_locations, name='api_search_locations'),
    path('api/search/members/', api_views.search_members, name='api_search_members'),
    path('api/search/categories/', api_views.search_categories, name='api_search_categories'),
    path('api/stock/info/', api_views.get_stock_info, name='api_stock_info'),
    path('api/categories/<int:category_id>/schema/', api_views.get_category_schema, name='api_category_schema'),
    path('api/categories/<int:category_id>/items/', api_views.get_items_by_category, name='api_category_items'),
    path('api/items/<int:item_id>/', api_views.get_item_details, name='api_item_details'),
    path('api/items/<int:item_id>/variants/', api_views.get_item_variants, name='api_item_variants'),
    path('api/items/recent/', api_views.get_recent_items, name='api_recent_items'),
    path('api/items/favorites/', api_views.get_favorite_items, name='api_favorite_items'),
    path('api/variants/', api_views.ItemVariantAPIView.as_view(), name='api_variants_create'),
    path('api/variants/<int:variant_id>/', api_views.ItemVariantAPIView.as_view(), name='api_variant_detail'),
    
    # AJAX Endpoints für Smart Transaktionen
    path('ajax/stock-info/', get_stock_info, name='get_stock_info'),
    path('ajax/filtered-locations/', get_filtered_locations, name='get_filtered_locations'),
    path('ajax/search-items/', search_items, name='search_items'),
    path('ajax/search-locations/', search_locations, name='search_locations'),
]