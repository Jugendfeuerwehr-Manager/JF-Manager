from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView
from django.urls import reverse_lazy
from django.db import transaction
from django.http import JsonResponse, HttpResponseRedirect
from django_tables2 import RequestConfig
from django_filters.views import FilterView
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from members.models import Member
from .models import Order, OrderableItem, OrderStatus, OrderItem
from .serializers import OrderSerializer, OrderableItemSerializer, OrderStatusSerializer, OrderItemSerializer
from .selectors import get_order_list, get_orderable_item_list, get_order_status_list
from .forms import (
    OrderForm, OrderItemFormSet, OrderFilter, OrderFilterFormHelper,
    OrderStatusUpdateForm, QuickOrderForm
)
from .tables import OrderTable


class OrderListView(LoginRequiredMixin, FilterView):
    """Listenansicht für Bestellungen"""
    model = Order
    table_class = OrderTable
    template_name = 'orders/order_list.html'
    filterset_class = OrderFilter
    context_object_name = 'orders'
    paginate_by = 25

    def get_queryset(self):
        return get_order_list()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'].form.helper = OrderFilterFormHelper()
        
        # Table für django-tables2
        table = OrderTable(self.filterset.qs)
        RequestConfig(self.request).configure(table)
        context['table'] = table
        
        # Statistiken
        queryset = self.filterset.qs
        context['stats'] = {
            'total_orders': queryset.count(),
            'pending_items': OrderItem.objects.filter(
                order__in=queryset,
                status__code='ORDERED'
            ).count(),
            'delivered_items': OrderItem.objects.filter(
                order__in=queryset,
                status__code='DELIVERED'
            ).count(),
        }
        
        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Detailansicht für Bestellungen"""
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.select_related('member', 'ordered_by').prefetch_related(
            'items__item', 'items__status'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_manage_orders'] = self.request.user.has_perm('orders.can_manage_orders')
        context['can_change_status'] = self.request.user.has_perm('orders.can_change_order_status')
        return context


class OrderCreateView(LoginRequiredMixin, CreateView):
    """Ansicht zum Erstellen neuer Bestellungen"""
    model = Order
    form_class = OrderForm
    template_name = 'orders/order_create.html'
    success_url = reverse_lazy('orders:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = OrderItemFormSet(self.request.POST)
        else:
            context['formset'] = OrderItemFormSet()
        context['orderable_items'] = OrderableItem.objects.filter(is_active=True)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        with transaction.atomic():
            form.instance.ordered_by = self.request.user
            self.object = form.save()
            
            if formset.is_valid():
                formset.instance = self.object
                items = formset.save(commit=False)
                
                # Default Status für neue Items setzen
                default_status = OrderStatus.objects.filter(code='ORDERED').first()
                if not default_status:
                    default_status = OrderStatus.objects.first()
                
                for item in items:
                    if not item.status_id:
                        item.status = default_status
                    item.save()
                
                formset.save_m2m()
                
                messages.success(
                    self.request, 
                    f'Bestellung für {self.object.member} wurde erfolgreich erstellt.'
                )
                return HttpResponseRedirect(self.get_success_url())
            else:
                return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Bitte korrigieren Sie die Fehler im Formular.')
        return super().form_invalid(form)


class QuickOrderCreateView(LoginRequiredMixin, FormView):
    """Schnelle Bestellung für häufig bestellte Artikel"""
    form_class = QuickOrderForm
    template_name = 'orders/quick_order.html'
    success_url = reverse_lazy('orders:list')

    def form_valid(self, form):
        member = form.cleaned_data['member']
        
        with transaction.atomic():
            # Neue Bestellung erstellen
            order = Order.objects.create(
                member=member,
                ordered_by=self.request.user,
                notes='Schnellbestellung'
            )
            
            # Default Status
            default_status = OrderStatus.objects.filter(code='ORDERED').first()
            if not default_status:
                default_status = OrderStatus.objects.first()
            
            # Ausgewählte Items hinzufügen
            items_added = 0
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('item_') and value:
                    item_id = field_name.split('_')[1]
                    item = OrderableItem.objects.get(id=item_id)
                    
                    # Größe prüfen
                    size_field = f'size_{item_id}'
                    size = form.cleaned_data.get(size_field, '')
                    
                    OrderItem.objects.create(
                        order=order,
                        item=item,
                        size=size,
                        quantity=1,
                        status=default_status
                    )
                    items_added += 1
            
            if items_added > 0:
                messages.success(
                    self.request, 
                    f'Schnellbestellung für {member} mit {items_added} Artikel(n) wurde erstellt.'
                )
            else:
                order.delete()
                messages.warning(self.request, 'Keine Artikel ausgewählt.')
                return self.form_invalid(form)
        
        return HttpResponseRedirect(self.get_success_url())


@login_required
@permission_required('orders.can_change_order_status', raise_exception=True)
def update_order_item_status(request, order_id, item_id):
    """Status eines Bestellartikels aktualisieren"""
    order = get_object_or_404(Order, id=order_id)
    order_item = get_object_or_404(OrderItem, id=item_id, order=order)
    
    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST, instance=order_item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Status für {order_item.item.name} wurde aktualisiert.')
            return redirect('orders:detail', pk=order.pk)
    else:
        form = OrderStatusUpdateForm(instance=order_item)
    
    return render(request, 'orders/update_status.html', {
        'form': form,
        'order': order,
        'order_item': order_item,
    })


@login_required
def get_item_sizes(request, item_id):
    """AJAX Endpoint für Größen eines Artikels"""
    try:
        item = OrderableItem.objects.get(id=item_id, is_active=True)
        sizes = item.get_sizes_list() if item.has_sizes else []
        return JsonResponse({
            'has_sizes': item.has_sizes,
            'sizes': sizes
        })
    except OrderableItem.DoesNotExist:
        return JsonResponse({'error': 'Artikel nicht gefunden'}, status=404)


############################ API ################################################

class OrderViewSet(viewsets.ModelViewSet):
    """
    API Endpoint für Bestellungen
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_order_list()
    serializer_class = OrderSerializer
    filterset_fields = ['member', 'ordered_by', 'order_date']
    search_fields = ['member__name', 'member__lastname', 'notes']


class OrderableItemViewSet(viewsets.ModelViewSet):
    """
    API Endpoint für bestellbare Artikel
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_orderable_item_list()
    serializer_class = OrderableItemSerializer
    filterset_fields = ['category', 'has_sizes', 'is_active']
    search_fields = ['name', 'category', 'description']


class OrderStatusViewSet(viewsets.ModelViewSet):
    """
    API Endpoint für Bestellstatus
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_order_status_list()
    serializer_class = OrderStatusSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    API Endpoint für Bestellartikel
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = OrderItem.objects.select_related('order', 'item', 'status')
    serializer_class = OrderItemSerializer
    filterset_fields = ['order', 'item', 'status', 'size']
    search_fields = ['item__name', 'notes']
