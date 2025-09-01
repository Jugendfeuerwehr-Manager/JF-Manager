from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.db import models as dj_models

from inventory.forms import DynamicItemForm
from inventory.forms.variant_forms import BulkVariantCreationForm, ItemVariantForm
from inventory.models import Item, ItemVariant, Stock, Category, Transaction


class ItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    permission_required = 'inventory.view_item'
    paginate_by = 20

    def get_queryset(self):
        # Prefetch variant stocks to avoid N+1 when rendering variants
        return (
            Item.objects.select_related('category')
            .prefetch_related('stock_set__location', 'variants__stock_set__location')
        )

    def get_context_data(self, **kwargs):  # pragma: no cover - template context assembly
        context = super().get_context_data(**kwargs)
        context['can_add_item'] = self.request.user.has_perm('inventory.add_item')
        context['filter_categories'] = Category.objects.order_by('name')
        items = context.get('items', [])
        item_ids = [i.id for i in items]
        loc_ids = Stock.objects.filter(item_id__in=item_ids).values_list('location_id', flat=True)
        variant_loc_ids = Stock.objects.filter(item_variant__parent_item_id__in=item_ids).values_list('location_id', flat=True)
        all_loc_ids = set(list(loc_ids) + list(variant_loc_ids))
        context['filter_locations'] = Stock.location.field.related_model.objects.filter(id__in=all_loc_ids).order_by('name')  # type: ignore
        return context


class ItemDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Item
    template_name = 'inventory/item_detail.html'
    permission_required = 'inventory.view_item'

    def get_context_data(self, **kwargs):  # pragma: no cover
        from django.db import models as dj_models
        context = super().get_context_data(**kwargs)
        context['stocks'] = self.object.stock_set.select_related('location').all()
        context['variant_stocks'] = Stock.objects.filter(item_variant__parent_item=self.object).select_related('location', 'item_variant')
        context['transactions'] = Transaction.objects.filter(
            dj_models.Q(item=self.object) | dj_models.Q(item_variant__parent_item=self.object)
        ).select_related('source', 'target', 'user', 'item', 'item_variant', 'item_variant__parent_item').order_by('-date')[:15]
        context['variants'] = ItemVariant.objects.filter(parent_item=self.object)
        perms = self.request.user
        context['can_change_item'] = perms.has_perm('inventory.change_item')
        context['can_delete_item'] = perms.has_perm('inventory.delete_item')
        context['can_add_transaction'] = perms.has_perm('inventory.add_transaction')
        return context


class ItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Item
    form_class = DynamicItemForm
    template_name = 'inventory/item_form_with_variants.html'
    permission_required = 'inventory.add_item'

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class ItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Item
    form_class = DynamicItemForm
    template_name = 'inventory/item_form_with_variants.html'
    permission_required = 'inventory.change_item'

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class ItemDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Item
    template_name = 'inventory/item_confirm_delete.html'
    permission_required = 'inventory.delete_item'
    success_url = reverse_lazy('inventory:item_list')

    def delete(self, request, *args, **kwargs):  # pragma: no cover
        self.object = self.get_object()
        messages.success(request, f'Artikel "{self.object.name}" wurde erfolgreich gelöscht.')
        return super().delete(request, *args, **kwargs)


class ItemVariantDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = ItemVariant
    template_name = 'inventory/variant_detail.html'
    permission_required = 'inventory.view_item'
    context_object_name = 'variant'

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        variant = self.object
        stocks = Stock.objects.filter(item_variant=variant).select_related('location')
        context['stocks'] = stocks
        context['total_stock'] = sum(stock.quantity for stock in stocks)
        context['recent_transactions'] = Transaction.objects.filter(
            item_variant=variant
        ).select_related('source', 'target', 'user').order_by('-date')[:10]
        perms = self.request.user
        context['can_edit_item'] = perms.has_perm('inventory.change_item')
        context['can_add_transaction'] = perms.has_perm('inventory.add_transaction')
        return context


class ItemVariantCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ItemVariant
    template_name = 'inventory/variant_form.html'
    permission_required = 'inventory.add_item'
    fields = ['parent_item', 'sku']

    def get_initial(self):  # pragma: no cover
        initial = super().get_initial()
        parent_id = self.request.GET.get('parent')
        if parent_id:
            try:
                initial['parent_item'] = Item.objects.get(pk=parent_id)
            except Item.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        parent = None
        parent_id = self.request.GET.get('parent') or self.request.POST.get('parent_item')
        if parent_id:
            try:
                parent = Item.objects.get(pk=parent_id)
            except Item.DoesNotExist:  # noqa: PERF203
                parent = None
        context['parent_item_obj'] = parent
        context['category_schema'] = parent.category.schema if parent and parent.category and parent.category.schema else {}
        return context

    def form_valid(self, form):  # pragma: no cover
        variant_attributes = {}
        for key, value in self.request.POST.items():
            if key.startswith('attr_') and value:
                variant_attributes[key.replace('attr_', '')] = value
        form.instance.variant_attributes = variant_attributes
        form.instance.parent_item.is_variant_parent = True
        form.instance.parent_item.save()
        return super().form_valid(form)

    def get_success_url(self):  # pragma: no cover
        return self.object.parent_item.get_absolute_url()


class BulkVariantCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Bulk-Erstellung von Artikel-Varianten"""
    form_class = BulkVariantCreationForm
    template_name = 'inventory/bulk_variant_form.html'
    permission_required = 'inventory.add_item'

    def get_parent_item(self):
        """Holt das Eltern-Item aus der URL"""
        parent_id = self.kwargs.get('parent_pk')
        return get_object_or_404(Item, pk=parent_id)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Remove instance kwarg as this is not a ModelForm
        kwargs.pop('instance', None)
        kwargs['parent_item'] = self.get_parent_item()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_item'] = self.get_parent_item()
        return context

    def form_valid(self, form):
        parent_item = self.get_parent_item()
        
        # Sicherstellen, dass das Item als Varianten-Parent markiert ist
        if not parent_item.is_variant_parent:
            parent_item.is_variant_parent = True
            parent_item.save()
        
        try:
            # Varianten erstellen
            created_variants = form.create_variants()
            
            # Erfolgs-Nachricht
            count = len(created_variants)
            if count == 1:
                messages.success(
                    self.request, 
                    f'1 Variante wurde erfolgreich erstellt.'
                )
            else:
                messages.success(
                    self.request, 
                    f'{count} Varianten wurden erfolgreich erstellt.'
                )
            
            # Details der erstellten Varianten anzeigen
            variant_names = [str(variant) for variant in created_variants[:5]]  # Nur die ersten 5 anzeigen
            if len(created_variants) > 5:
                variant_names.append(f'... und {len(created_variants) - 5} weitere')
            
            messages.info(
                self.request,
                f'Erstellt: {", ".join(variant_names)}'
            )
            
        except Exception as e:
            messages.error(
                self.request, 
                f'Fehler beim Erstellen der Varianten: {str(e)}'
            )
            return self.form_invalid(form)
        
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.get_parent_item().get_absolute_url()


class ItemVariantUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Einzelne Variante bearbeiten"""
    model = ItemVariant
    form_class = ItemVariantForm
    template_name = 'inventory/variant_form.html'
    permission_required = 'inventory.change_item'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parent_item'] = self.object.parent_item
        return kwargs

    def get_success_url(self):
        return self.object.parent_item.get_absolute_url()


class ItemVariantDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Variante löschen"""
    model = ItemVariant
    template_name = 'inventory/variant_confirm_delete.html'
    permission_required = 'inventory.delete_item'

    def get_success_url(self):
        return self.object.parent_item.get_absolute_url()

    def delete(self, request, *args, **kwargs):
        variant = self.get_object()
        parent_item = variant.parent_item
        variant_name = str(variant)
        
        result = super().delete(request, *args, **kwargs)
        
        messages.success(
            request, 
            f'Variante "{variant_name}" wurde erfolgreich gelöscht.'
        )
        
        # Prüfen, ob noch andere Varianten existieren
        remaining_variants = ItemVariant.objects.filter(parent_item=parent_item).count()
        if remaining_variants == 0:
            parent_item.is_variant_parent = False
            parent_item.save()
            messages.info(
                request,
                f'"{parent_item.name}" hat keine Varianten mehr und wurde als normaler Artikel markiert.'
            )
        
        return result
