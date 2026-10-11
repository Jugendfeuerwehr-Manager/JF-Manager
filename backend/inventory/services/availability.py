"""Available, issued and ordered quantities per article or size (UX-05.1).

Read-only aggregation over the booked stock and the open order lines. Stock
changes stay with the booking service (``Transaction.update_stock``).
"""

from django.db.models import Q, Sum

from inventory.api.access import filter_item_department_queryset_for_user, visible_item_department_ids
from inventory.models import Item, ItemVariant, Stock
from orders.models import OrderItem
from orders.notifications import OrderWorkflowService

# Order lines that still wait for delivery into stock: neither received, delivered nor cancelled.
OPEN_ORDER_STATUS_CODES = tuple(OrderWorkflowService.STATUS_CATEGORIES["actionable"])


def visible_items(user):
    """Items the user may read, with the same scope as the item list (central records included)."""
    allowed_ids = visible_item_department_ids(user, "inventory.view_item")
    items = Item.objects.all()
    if allowed_ids is None:
        return items
    if not allowed_ids:
        return items.none()
    return items.filter(Q(department_id__in=allowed_ids) | Q(department__isnull=True))


def match_variant(variants, size):
    """Return the one variant whose attribute values contain ``size`` (same rule as the order receipt)."""
    if not size:
        return None
    matches = [
        variant
        for variant in variants
        if str(size) in {str(value) for value in (variant.variant_attributes or {}).values()}
    ]
    return matches[0] if len(matches) == 1 else None


def stock_availability(user, item_ids=None):
    """Return one row per article or size with available, issued and ordered quantities.

    ``available`` counts stock at storage locations, ``issued`` stock at member
    locations. ``ordered`` counts open order lines the user may read; it is
    ``None`` without any order read right. Order lines whose size matches no
    single variant are reported on the article row with ``item_variant=None``.
    """
    items = visible_items(user)
    if item_ids:
        items = items.filter(pk__in=item_ids)
    items = list(items.prefetch_related("variants"))

    order_department_ids = visible_item_department_ids(user, "orders.view_order")
    can_view_orders = order_department_ids is None or bool(order_department_ids)
    rows = {}

    def row(item_id, variant_id):
        key = (item_id, variant_id)
        if key not in rows:
            rows[key] = {
                "item": item_id,
                "item_variant": variant_id,
                "available": 0,
                "issued": 0,
                "ordered": 0 if can_view_orders else None,
            }
        return rows[key]

    variants_by_item = {}
    for item in items:
        if item.is_variant_parent:
            variants_by_item[item.pk] = list(item.variants.all())
            for variant in variants_by_item[item.pk]:
                row(item.pk, variant.pk)
        else:
            row(item.pk, None)

    item_pks = [item.pk for item in items]
    stocks = filter_item_department_queryset_for_user(
        Stock.objects.filter(Q(item_id__in=item_pks) | Q(item_variant__parent_item_id__in=item_pks)),
        user,
        "inventory.view_stock",
    )
    for entry in stocks.values(
        "item_id", "item_variant_id", "item_variant__parent_item_id", "location__is_member"
    ).annotate(total=Sum("quantity")):
        target = row(entry["item_id"] or entry["item_variant__parent_item_id"], entry["item_variant_id"])
        target["issued" if entry["location__is_member"] else "available"] += entry["total"] or 0

    if can_view_orders and item_pks:
        open_lines = OrderItem.objects.filter(
            receipt_transaction__isnull=True,
            status__code__in=OPEN_ORDER_STATUS_CODES,
            item__inventory_item_id__in=item_pks,
        )
        if order_department_ids is not None:
            open_lines = open_lines.filter(order__department_id__in=order_department_ids)
        for entry in open_lines.values("item__inventory_item_id", "size").annotate(total=Sum("quantity")):
            item_id = entry["item__inventory_item_id"]
            variant = match_variant(variants_by_item.get(item_id, []), entry["size"])
            row(item_id, variant.pk if variant else None)["ordered"] += entry["total"] or 0

    return {"can_view_orders": can_view_orders, "results": list(rows.values())}


def lookup_code(items, code):
    """Find articles or sizes by inventory number, barcode or size article number (case-insensitive)."""
    results = []
    for item in items.filter(Q(identifier1__iexact=code) | Q(identifier2__iexact=code)).order_by("name"):
        results.append(
            {
                "item": item.pk,
                "item_variant": None,
                "label": str(item),
                "is_variant_parent": item.is_variant_parent,
            }
        )
    variants = (
        ItemVariant.objects.filter(parent_item__in=items, sku__iexact=code)
        .select_related("parent_item")
        .order_by("parent_item__name", "pk")
    )
    for variant in variants:
        results.append(
            {
                "item": variant.parent_item_id,
                "item_variant": variant.pk,
                "label": str(variant),
                "is_variant_parent": False,
            }
        )
    return results
