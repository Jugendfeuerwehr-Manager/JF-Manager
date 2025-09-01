from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from inventory.models import StorageLocation, Stock, Item, ItemVariant


@login_required
@require_http_methods(["GET"])
def get_stock_info(request):
    """Get stock information for a specific item at a location"""
    item_id = request.GET.get('item_id')
    variant_id = request.GET.get('variant_id')
    location_id = request.GET.get('location_id')
    
    if not location_id:
        return JsonResponse({'error': 'Location ID required'}, status=400)
    
    try:
        location = StorageLocation.objects.get(id=location_id)
        
        # Build stock filter
        stock_filter = {'location': location}
        if item_id:
            stock_filter.update({'item_id': item_id, 'item_variant': None})
        elif variant_id:
            stock_filter.update({'item': None, 'item_variant_id': variant_id})
        else:
            return JsonResponse({'error': 'Item or variant ID required'}, status=400)
        
        try:
            stock = Stock.objects.get(**stock_filter)
            return JsonResponse({
                'quantity': stock.quantity,
                'location_name': location.name,
                'item_name': stock.item.name if stock.item else str(stock.item_variant)
            })
        except Stock.DoesNotExist:
            return JsonResponse({
                'quantity': 0,
                'location_name': location.name,
                'item_name': 'Unknown'
            })
            
    except StorageLocation.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)


@login_required
@require_http_methods(["GET"])
def get_filtered_locations(request):
    """Get filtered storage locations based on criteria"""
    filter_type = request.GET.get('filter_type')
    item_id = request.GET.get('item_id')
    variant_id = request.GET.get('variant_id')
    
    locations = StorageLocation.objects.all()
    
    if filter_type == 'positive_stock':
        # Filter locations with positive stock for the specified item
        if item_id or variant_id:
            stock_filter = Q(stocks__quantity__gt=0)
            if item_id:
                stock_filter &= Q(stocks__item_id=item_id)
            if variant_id:
                stock_filter &= Q(stocks__item_variant_id=variant_id)
            
            locations = locations.filter(stock_filter).distinct()
    
    elif filter_type == 'member_locations':
        # Filter locations that are assigned to members
        locations = locations.filter(assigned_members__isnull=False).distinct()
    
    # Convert to hierarchical list
    locations_data = []
    sorted_locations = _sort_locations_hierarchically(locations)
    
    for location in sorted_locations:
        indent = '  ' * getattr(location, '_display_level', 0)
        locations_data.append({
            'id': location.id,
            'name': f"{indent}{location.name}",
            'full_path': location.get_full_path() if hasattr(location, 'get_full_path') else location.name
        })
    
    return JsonResponse({'locations': locations_data})


def _sort_locations_hierarchically(locations):
    """Sort locations in hierarchical order"""
    # Convert to list to avoid multiple DB queries
    location_list = list(locations.select_related('parent'))
    location_dict = {loc.id: loc for loc in location_list}
    
    # Find root locations
    roots = [loc for loc in location_list if loc.parent_id is None]
    sorted_list = []
    
    def add_location_with_children(location, level=0):
        location._display_level = level
        sorted_list.append(location)
        
        # Find children
        children = [loc for loc in location_list if loc.parent_id == location.id]
        children.sort(key=lambda x: x.name)
        
        for child in children:
            add_location_with_children(child, level + 1)
    
    # Sort roots by name and add them with their children
    roots.sort(key=lambda x: x.name)
    for root in roots:
        add_location_with_children(root)
    
    return sorted_list


@login_required
@require_http_methods(["GET"])
def search_items(request):
    """Search for items and variants"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'items': [], 'variants': []})
    
    # Search items
    items = Item.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_variant_parent=False
    ).select_related('category')[:10]
    
    # Search variants
    variants = ItemVariant.objects.filter(
        Q(name__icontains=query) | Q(parent_item__name__icontains=query)
    ).select_related('parent_item', 'parent_item__category')[:10]
    
    items_data = []
    for item in items:
        items_data.append({
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else '',
            'type': 'item'
        })
    
    variants_data = []
    for variant in variants:
        variants_data.append({
            'id': variant.id,
            'name': variant.name,
            'parent_name': variant.parent_item.name,
            'category': variant.parent_item.category.name if variant.parent_item.category else '',
            'type': 'variant'
        })
    
    return JsonResponse({
        'items': items_data,
        'variants': variants_data
    })


@login_required
@require_http_methods(["GET"])
def search_locations(request):
    """Search for storage locations"""
    query = request.GET.get('q', '').strip()
    location_type = request.GET.get('type', 'all')  # 'all', 'member', 'stock'
    
    if len(query) < 2:
        return JsonResponse({'locations': []})
    
    locations = StorageLocation.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    )
    
    # Apply type filtering
    if location_type == 'member':
        locations = locations.filter(assigned_members__isnull=False)
    elif location_type == 'stock':
        locations = locations.filter(stocks__quantity__gt=0)
    
    locations = locations.distinct().select_related('parent')[:15]
    
    locations_data = []
    for location in locations:
        locations_data.append({
            'id': location.id,
            'name': location.name,
            'full_path': location.get_full_path() if hasattr(location, 'get_full_path') else location.name,
            'member_count': location.assigned_members.count() if hasattr(location, 'assigned_members') else 0
        })
    
    return JsonResponse({'locations': locations_data})
