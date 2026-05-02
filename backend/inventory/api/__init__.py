"""Inventory DRF API package — public surface.

ViewSets are split by domain into focused modules:
- item_viewsets.py       → CategoryViewSet, ItemViewSet, ItemVariantViewSet
- location_viewsets.py   → StorageLocationViewSet
- stock_transaction_viewsets.py → StockViewSet, TransactionViewSet

All are re-exported here so rest_urls.py has a single import point.
"""

from inventory.api.item_viewsets import CategoryViewSet, ItemVariantViewSet, ItemViewSet
from inventory.api.location_viewsets import StorageLocationViewSet
from inventory.api.stock_transaction_viewsets import StockViewSet, TransactionViewSet

__all__ = [
    "CategoryViewSet",
    "ItemVariantViewSet",
    "ItemViewSet",
    "StockViewSet",
    "StorageLocationViewSet",
    "TransactionViewSet",
]
