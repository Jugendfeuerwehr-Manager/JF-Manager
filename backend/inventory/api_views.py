"""
API Views für AJAX-Anfragen im Inventar-System
"""
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json

from .models import Item, ItemVariant, StorageLocation, Stock, Category
from members.models.member import Member


def _deprecated(response: JsonResponse):  # helper
    response['X-Deprecated'] = 'true'
    response['Link'] = 'See /api/v1/inventory/... for new endpoints'
    return response


@login_required
@permission_required('inventory.view_item', raise_exception=True)
@require_GET
def search_items(request):
    """AJAX-Endpunkt für die Artikel-Suche"""
    query = request.GET.get('q', '').strip()
    location_id = request.GET.get('location_id')
    category_id = request.GET.get('category_id')
    page = request.GET.get('page', 1)
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'has_more': False})
    
    # Basis-Queryset
    items = Item.objects.select_related('category').all()
    
    # Nach Text suchen
    items = items.filter(
        Q(name__icontains=query) |
        Q(category__name__icontains=query)
    )
    
    # Nach Kategorie filtern
    if category_id:
        items = items.filter(category_id=category_id)
    
    # Nach Lagerort filtern (nur Items mit Bestand)
    if location_id:
        items = items.filter(
            stock__location_id=location_id,
            stock__quantity__gt=0
        ).distinct()
    
    # Paginierung
    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(page)
    
    results = []
    for item in page_obj:
        # Bestandsinformationen hinzufügen
        stock_info = {}
        if location_id:
            try:
                stock = Stock.objects.get(item=item, location_id=location_id)
                stock_info = {
                    'quantity': stock.quantity,
                    'location_name': stock.location.name
                }
            except Stock.DoesNotExist:
                stock_info = {'quantity': 0, 'location_name': ''}
        else:
            # Gesamtbestand über alle Lagerorte
            total_stock = Stock.objects.filter(item=item).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            stock_info = {'total_quantity': total_stock}
        
        results.append({
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else '',
            'display_name': f"{item.name} ({item.category.name})" if item.category else item.name,
            'stock': stock_info
        })
    
    return _deprecated(JsonResponse({
        'results': results,
        'has_more': page_obj.has_next(),
        'total_count': paginator.count
    }))


@login_required
@permission_required('inventory.view_storagelocation', raise_exception=True)
@require_GET
def search_locations(request):
    """AJAX-Endpunkt für die Lagerort-Suche"""
    query = request.GET.get('q', '').strip()
    exclude_member_locations = request.GET.get('exclude_members', '').lower() == 'true'
    page = request.GET.get('page', 1)
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'has_more': False})
    
    # Basis-Queryset
    locations = StorageLocation.objects.select_related('parent', 'member').all()
    
    # Nach Text suchen
    locations = locations.filter(
        Q(name__icontains=query) |
        Q(parent__name__icontains=query)
    )
    
    # Mitglieder-Lagerorte ausschließen falls gewünscht
    if exclude_member_locations:
        locations = locations.filter(is_member=False)
    
    # Hierarchisch sortieren
    locations = locations.order_by('parent__name', 'name')
    
    # Paginierung
    paginator = Paginator(locations, 20)
    page_obj = paginator.get_page(page)
    
    results = []
    for location in page_obj:
        # Bestandsstatistiken
        stock_count = Stock.objects.filter(location=location).count()
        total_items = Stock.objects.filter(location=location).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        results.append({
            'id': location.id,
            'name': location.name,
            'full_path': location.get_full_path(),
            'is_member': location.is_member,
            'member_name': str(location.member) if location.member else '',
            'stock_info': {
                'unique_items': stock_count,
                'total_quantity': total_items
            }
        })
    
    return _deprecated(JsonResponse({
        'results': results,
        'has_more': page_obj.has_next(),
        'total_count': paginator.count
    }))


@login_required
@permission_required('members.view_member', raise_exception=True)
@require_GET
def search_members(request):
    """AJAX-Endpunkt für die Mitglieder-Suche - nur notwendige Daten"""
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'has_more': False})
    
    # Basis-Queryset
    members = Member.objects.select_related('group', 'status').all()
    
    # Nach Text suchen - nur in Name und Nachname
    members = members.filter(
        Q(name__icontains=query) |
        Q(lastname__icontains=query)
    )
    
    # Pagination
    paginator = Paginator(members, 20)
    try:
        page_obj = paginator.page(page)
        members_page = page_obj.object_list
        has_more = page_obj.has_next()
    except:
        members_page = []
        has_more = False
    
    results = []
    for member in members_page:
        # Nur notwendige Daten für Autocomplete - keine sensiblen Informationen
        full_name = f"{member.name} {member.lastname}".strip()
        
        # Nur Gruppenname als zusätzliche Info (falls vorhanden)
        detail = member.group.name if member.group else None
        
        results.append({
            'id': member.id,
            'text': full_name,
            'detail': detail
        })
    
    return _deprecated(JsonResponse({
        'results': results,
        'has_more': has_more
    }))


@login_required
@permission_required('inventory.view_stock', raise_exception=True)
@require_GET
def get_stock_info(request):
    """AJAX-Endpunkt für Bestandsinformationen"""
    item_id = request.GET.get('item_id')
    variant_id = request.GET.get('variant_id')
    location_id = request.GET.get('location_id')
    
    if not item_id and not variant_id:
        return JsonResponse({'error': 'Item ID or Variant ID required'}, status=400)
    
    try:
        if variant_id:
            variant = ItemVariant.objects.get(pk=variant_id)
            item_name = str(variant)
            stock_filter = {'item_variant': variant}
        else:
            item = Item.objects.get(pk=item_id)
            item_name = item.name
            stock_filter = {'item': item}
    except (Item.DoesNotExist, ItemVariant.DoesNotExist):
        return JsonResponse({'error': 'Item or Variant not found'}, status=404)
    
    stock_data = {}
    
    if location_id:
        # Bestand an spezifischem Lagerort
        try:
            location = StorageLocation.objects.get(pk=location_id)
            try:
                stock = Stock.objects.get(location=location, **stock_filter)
                stock_data = {
                    'location_name': location.get_full_path(),
                    'quantity': stock.quantity,
                    'has_stock': stock.quantity > 0
                }
            except Stock.DoesNotExist:
                stock_data = {
                    'location_name': location.get_full_path(),
                    'quantity': 0,
                    'has_stock': False
                }
        except StorageLocation.DoesNotExist:
            return JsonResponse({'error': 'Location not found'}, status=404)
    else:
        # Bestand über alle Lagerorte
        stocks = Stock.objects.filter(**stock_filter).select_related('location')
        total_quantity = sum(stock.quantity for stock in stocks)
        
        stock_data = {
            'item_name': item_name,
            'total_quantity': total_quantity,
            'locations': [
                {
                    'location_name': stock.location.get_full_path(),
                    'quantity': stock.quantity
                }
                for stock in stocks if stock.quantity > 0
            ]
        }
    
    return _deprecated(JsonResponse({'stock': stock_data}))


@login_required
@require_GET
def search_categories(request):
    """AJAX-Endpunkt für die Kategorie-Suche"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    categories = Category.objects.filter(
        name__icontains=query
    ).order_by('name')[:20]
    
    results = [
        {
            'id': category.id,
            'name': category.name,
            'item_count': category.items.count()
        }
        for category in categories
    ]
    
    return _deprecated(JsonResponse({'results': results}))


@login_required
@require_GET
def get_category_schema(request, category_id):
    """AJAX-Endpunkt für das Kategorie-Schema"""
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    
    # Schema parsen
    schema = {}
    if category.schema:
        try:
            schema = category.schema if isinstance(category.schema, dict) else {}
        except (ValueError, TypeError):
            schema = {}
    
    return _deprecated(JsonResponse({
        'category': {
            'id': category.id,
            'name': category.name
        },
        'schema': schema
    }))


@login_required
@require_GET
def get_items_by_category(request, category_id):
    """AJAX-Endpunkt für Artikel einer bestimmten Kategorie"""
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    
    items = Item.objects.filter(category=category).select_related('category')
    
    # Bestandsinformationen hinzufügen
    results = []
    for item in items:
        stocks = Stock.objects.filter(item=item).select_related('location')
        total_quantity = sum(stock.quantity for stock in stocks)
        
        results.append({
            'id': item.id,
            'name': item.name,
            'total_stock': total_quantity,
            'locations': [
                {
                    'location_id': stock.location.id,
                    'location_name': stock.location.get_full_path(),
                    'quantity': stock.quantity
                }
                for stock in stocks if stock.quantity > 0
            ]
        })
    
    return _deprecated(JsonResponse({
        'category': {
            'id': category.id,
            'name': category.name
        },
        'items': results
    }))


@login_required
@require_GET
def get_item_variants(request, item_id):
    """AJAX-Endpunkt für Varianten eines Items"""
    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    
    if not item.is_variant_parent:
        return JsonResponse({'variants': []})
    
    variants = ItemVariant.objects.filter(parent_item=item).prefetch_related('stock_set')
    
    results = []
    for variant in variants:
        total_stock = variant.stock_set.aggregate(total=Sum('quantity'))['total'] or 0
        
        results.append({
            'id': variant.id,
            'sku': variant.sku,
            'variant_attributes': variant.variant_attributes,
            'total_stock': total_stock,
            'display_name': str(variant)
        })
    
    return _deprecated(JsonResponse({'variants': results}))


@login_required
@require_GET  
def get_item_details(request, item_id):
    """AJAX-Endpunkt für Item-Details inklusive Kategorie"""
    try:
        item = Item.objects.select_related('category').get(pk=item_id)
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    
    result = {
        'id': item.id,
        'name': item.name,
        'is_variant_parent': item.is_variant_parent,
        'attributes': item.attributes,
        'category': None
    }
    
    if item.category:
        result['category'] = {
            'id': item.category.id,
            'name': item.category.name,
            'schema': item.category.schema or {}
        }
    
    return _deprecated(JsonResponse(result))


@method_decorator([login_required, permission_required('inventory.view_itemvariant', raise_exception=True)], name='dispatch')
class ItemVariantAPIView(View):
    """API View für ItemVariant CRUD-Operationen"""
    
    def get(self, request, variant_id):
        """GET einzelne Variante"""
        try:
            variant = ItemVariant.objects.select_related('parent_item__category').get(pk=variant_id)
        except ItemVariant.DoesNotExist:
            return JsonResponse({'error': 'Variant not found'}, status=404)
        
        total_stock = variant.stock_set.aggregate(total=Sum('quantity'))['total'] or 0
        
        return JsonResponse({
            'id': variant.id,
            'parent_item': variant.parent_item.id,
            'sku': variant.sku,
            'variant_attributes': variant.variant_attributes,
            'total_stock': total_stock,
            'display_name': str(variant)
        })
    
    @method_decorator(csrf_exempt)
    def post(self, request):
        """POST neue Variante erstellen"""
        # Zusätzliche Berechtigung für das Erstellen
        if not request.user.has_perm('inventory.add_itemvariant'):
            return JsonResponse({'error': 'Keine Berechtigung zum Erstellen von Varianten'}, status=403)
            
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        try:
            parent_item = Item.objects.get(pk=data.get('parent_item'))
        except Item.DoesNotExist:
            return JsonResponse({'error': 'Parent item not found'}, status=404)
        
        # Ensure parent item is marked as variant parent
        if not parent_item.is_variant_parent:
            parent_item.is_variant_parent = True
            parent_item.save()
        
        # Create variant
        variant = ItemVariant.objects.create(
            parent_item=parent_item,
            sku=data.get('sku', ''),
            variant_attributes=data.get('variant_attributes', {})
        )
        
        return JsonResponse({
            'id': variant.id,
            'sku': variant.sku,
            'variant_attributes': variant.variant_attributes,
            'display_name': str(variant)
        }, status=201)
    
    @method_decorator(csrf_exempt)
    def put(self, request, variant_id):
        """PUT Variante aktualisieren"""
        # Zusätzliche Berechtigung für das Ändern
        if not request.user.has_perm('inventory.change_itemvariant'):
            return JsonResponse({'error': 'Keine Berechtigung zum Ändern von Varianten'}, status=403)
            
        try:
            variant = ItemVariant.objects.get(pk=variant_id)
        except ItemVariant.DoesNotExist:
            return JsonResponse({'error': 'Variant not found'}, status=404)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Update fields
        variant.sku = data.get('sku', variant.sku)
        variant.variant_attributes = data.get('variant_attributes', variant.variant_attributes)
        variant.save()
        
        return JsonResponse({
            'id': variant.id,
            'sku': variant.sku,
            'variant_attributes': variant.variant_attributes,
            'display_name': str(variant)
        })
    
    @method_decorator(csrf_exempt)
    def delete(self, request, variant_id):
        """DELETE Variante löschen"""
        # Zusätzliche Berechtigung für das Löschen
        if not request.user.has_perm('inventory.delete_itemvariant'):
            return JsonResponse({'error': 'Keine Berechtigung zum Löschen von Varianten'}, status=403)
            
        try:
            variant = ItemVariant.objects.get(pk=variant_id)
        except ItemVariant.DoesNotExist:
            return JsonResponse({'error': 'Variant not found'}, status=404)
        
        # Check if variant has stock
        total_stock = variant.stock_set.aggregate(total=Sum('quantity'))['total'] or 0
        if total_stock > 0:
            return JsonResponse({
                'error': f'Cannot delete variant with existing stock ({total_stock} items)'
            }, status=400)
        
        variant.delete()
        return JsonResponse({'success': True})


@login_required
@require_GET
def search_items_and_variants(request):
    """AJAX-Endpunkt für die Suche nach Items und Varianten"""
    query = request.GET.get('q', '').strip()
    location_id = request.GET.get('location_id')
    category_id = request.GET.get('category_id')
    page = request.GET.get('page', 1)
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'has_more': False})
    
    results = []
    
    # Search in Items
    items = Item.objects.select_related('category').filter(
        Q(name__icontains=query) |
        Q(category__name__icontains=query)
    )
    
    if category_id:
        items = items.filter(category_id=category_id)
    
    for item in items:
        # Skip variant parents in search results - show variants instead
        if item.is_variant_parent:
            continue
            
        # Stock information
        stock_info = {}
        if location_id:
            try:
                stock = Stock.objects.get(item=item, location_id=location_id)
                stock_info = {
                    'quantity': stock.quantity,
                    'location_name': stock.location.name
                }
            except Stock.DoesNotExist:
                stock_info = {'quantity': 0, 'location_name': ''}
        else:
            total_stock = Stock.objects.filter(item=item).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            stock_info = {'total_quantity': total_stock}
        
        results.append({
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else '',
            'display_name': f"{item.name} ({item.category.name})" if item.category else item.name,
            'type': 'item',
            'stock': stock_info
        })
    
    # Search in ItemVariants
    variants = ItemVariant.objects.select_related('parent_item__category').filter(
        Q(parent_item__name__icontains=query) |
        Q(parent_item__category__name__icontains=query) |
        Q(sku__icontains=query)
    )
    
    for variant in variants:
        # Stock information
        stock_info = {}
        if location_id:
            try:
                stock = Stock.objects.get(item_variant=variant, location_id=location_id)
                stock_info = {
                    'quantity': stock.quantity,
                    'location_name': stock.location.name
                }
            except Stock.DoesNotExist:
                stock_info = {'quantity': 0, 'location_name': ''}
        else:
            total_stock = Stock.objects.filter(item_variant=variant).aggregate(
                total=Sum('quantity')
            )['total'] or 0
            stock_info = {'total_quantity': total_stock}
        
        # Create attributes display
        variant_display = []
        if variant.variant_attributes:
            for key, value in variant.variant_attributes.items():
                variant_display.append(f"{key}: {value}")
        
        results.append({
            'id': f"variant_{variant.id}",
            'variant_id': variant.id,
            'name': str(variant),
            'category': variant.parent_item.category.name if variant.parent_item.category else '',
            'display_name': str(variant),
            'type': 'variant',
            'stock': stock_info,
            'attributes_display': ', '.join(variant_display)
        })
    
    # Simple pagination (can be enhanced)
    paginator = Paginator(results, 20)
    page_obj = paginator.get_page(page)
    
    return _deprecated(JsonResponse({
        'results': list(page_obj),
        'has_more': page_obj.has_next(),
        'total_count': len(results)
    }))


@login_required
@require_GET
def get_recent_items(request):
    """AJAX-Endpunkt für kürzlich verwendete Artikel"""
    # Für jetzt eine einfache Implementierung - die letzten 10 Artikel
    recent_items = Item.objects.select_related('category').order_by('-id')[:10]
    
    results = []
    for item in recent_items:
        results.append({
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else '',
            'display_name': f"{item.name} ({item.category.name})" if item.category else item.name
        })
    
    return _deprecated(JsonResponse({
        'results': results,
        'has_more': False,
        'total_count': len(results)
    }))


@login_required
@require_GET
def get_favorite_items(request):
    """AJAX-Endpunkt für Favoriten-Artikel"""
    # Für jetzt eine einfache Implementierung - die ersten 10 Artikel
    favorite_items = Item.objects.select_related('category').order_by('name')[:10]
    
    results = []
    for item in favorite_items:
        results.append({
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else '',
            'display_name': f"{item.name} ({item.category.name})" if item.category else item.name
        })
    
    return _deprecated(JsonResponse({
        'results': results,
        'has_more': False,
        'total_count': len(results)
    }))
