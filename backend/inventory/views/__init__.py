"""Inventory Django views package.

Previously all class-based views & AJAX helpers lived in a single, very long
`views.py` file (>1000 LOC). They are now split by domain for readability.

Public imports are re-exported to keep existing import paths working:

    from inventory.views import ItemListView
    from inventory import views; views.get_stock_info(...)

Remove re-exports only after all external references are updated.
"""

from .items import (
    ItemListView, ItemDetailView, ItemCreateView, ItemUpdateView, ItemDeleteView,
    ItemVariantDetailView, ItemVariantCreateView, BulkVariantCreateView, ItemVariantUpdateView, ItemVariantDeleteView,
)
from .stock import StockListView
from .transactions import (
    TransactionListView, TransactionCreateView, TransactionDetailView, ImprovedTransactionCreateView,
)
from .members import MemberLoanListView
from .dashboard import InventoryDashboardView
from .categories import (
    CategoryListView, CategoryDetailView, CategoryCreateView, CategoryUpdateView, CategoryDeleteView, CategoryBrowserView,
)
from .locations import (
    StorageLocationListView, StorageLocationDetailView, StorageLocationCreateView, StorageLocationUpdateView, StorageLocationDeleteView,
)
from .ajax_legacy import (
    get_stock_info, get_filtered_locations, search_items, search_locations,
)

__all__ = [
    # items / variants
    'ItemListView', 'ItemDetailView', 'ItemCreateView', 'ItemUpdateView', 'ItemDeleteView',
    'ItemVariantDetailView', 'ItemVariantCreateView',
    # stock
    'StockListView',
    # transactions
    'TransactionListView', 'TransactionCreateView', 'TransactionDetailView', 'ImprovedTransactionCreateView',
    # members
    'MemberLoanListView',
    # dashboard
    'InventoryDashboardView',
    # categories
    'CategoryListView', 'CategoryDetailView', 'CategoryCreateView', 'CategoryUpdateView', 'CategoryDeleteView', 'CategoryBrowserView',
    # locations
    'StorageLocationListView', 'StorageLocationDetailView', 'StorageLocationCreateView', 'StorageLocationUpdateView', 'StorageLocationDeleteView',
    # ajax legacy
    'get_stock_info', 'get_filtered_locations', 'search_items', 'search_locations',
]
