from .models import OrderStatus, OrderableItem, Order, OrderItem


def get_order_list():
    """Gibt alle Bestellungen zurück"""
    return Order.objects.select_related('member', 'ordered_by').prefetch_related('items__item', 'items__status')


def get_orderable_item_list():
    """Gibt alle bestellbaren Artikel zurück"""
    return OrderableItem.objects.filter(is_active=True).order_by('category', 'name')


def get_order_status_list():
    """Gibt alle aktiven Bestellstatus zurück"""
    return OrderStatus.objects.filter(is_active=True).order_by('sort_order')


def get_orders_by_member(member):
    """Gibt alle Bestellungen eines Mitglieds zurück"""
    return Order.objects.filter(member=member).select_related('ordered_by').prefetch_related('items__item', 'items__status')


def get_pending_orders():
    """Gibt alle nicht abgeschlossenen Bestellungen zurück"""
    delivered_status = OrderStatus.objects.filter(code='DELIVERED').first()
    cancelled_status = OrderStatus.objects.filter(code='CANCELLED').first()
    
    exclude_statuses = []
    if delivered_status:
        exclude_statuses.append(delivered_status.pk)
    if cancelled_status:
        exclude_statuses.append(cancelled_status.pk)
    
    return Order.objects.exclude(
        items__status__pk__in=exclude_statuses
    ).distinct().select_related('member', 'ordered_by')
