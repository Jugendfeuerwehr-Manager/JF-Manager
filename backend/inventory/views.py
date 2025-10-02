import crispy_forms
from crispy_forms.layout import Submit, Layout

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.db import models
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    TemplateView, UpdateView, DeleteView, CreateView, 
    ListView, DetailView
)

from inventory.forms.transaction_improved import ImprovedTransactionForm
from members.models import Member

from .forms import DynamicItemForm, TransactionForm, CategoryForm, StorageLocationForm
from .models import Item, ItemVariant, Transaction, Stock, StorageLocation, Category
from .selectors import get_item_list, get_category_list


# ====================
# Artikel Views
# ====================

class ItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Übersicht aller Artikel"""
    model = Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    permission_required = 'inventory.view_item'
    paginate_by = 20
    
    def get_queryset(self):
        return Item.objects.select_related('category').prefetch_related('stock_set__location')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_add_item'] = self.request.user.has_perm('inventory.add_item')
        context['filter_categories'] = Category.objects.order_by('name')
        items = context.get('items', [])
        item_ids = [i.id for i in items]
        loc_ids = Stock.objects.filter(item_id__in=item_ids).values_list('location_id', flat=True)
        variant_loc_ids = Stock.objects.filter(item_variant__parent_item_id__in=item_ids).values_list('location_id', flat=True)
        all_loc_ids = set(list(loc_ids) + list(variant_loc_ids))
        context['filter_locations'] = StorageLocation.objects.filter(id__in=all_loc_ids).order_by('name')
        return context


class ItemDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detail-Ansicht eines Artikels"""
    model = Item
    template_name = 'inventory/item_detail.html'
    permission_required = 'inventory.view_item'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Bestände sowohl für Item als auch Varianten aggregieren
        context['stocks'] = self.object.stock_set.select_related('location').all()
        context['variant_stocks'] = Stock.objects.filter(item_variant__parent_item=self.object).select_related('location', 'item_variant')
        # Transaktionen: sowohl direkte Item-Transaktionen als auch Variantentransaktionen des Items
        context['transactions'] = Transaction.objects.filter(
            models.Q(item=self.object) | models.Q(item_variant__parent_item=self.object)
        ).select_related('source', 'target', 'user', 'item', 'item_variant', 'item_variant__parent_item').order_by('-date')[:15]
        context['variants'] = ItemVariant.objects.filter(parent_item=self.object)
        context['can_change_item'] = self.request.user.has_perm('inventory.change_item')
        context['can_delete_item'] = self.request.user.has_perm('inventory.delete_item')
        context['can_add_transaction'] = self.request.user.has_perm('inventory.add_transaction')
        return context


class ItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Erstellen eines neuen Items"""
    model = Item
    form_class = DynamicItemForm
    template_name = 'inventory/item_form_with_variants.html'
    permission_required = 'inventory.add_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class ItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Bearbeiten eines Items"""
    model = Item
    form_class = DynamicItemForm
    template_name = 'inventory/item_form_with_variants.html'
    permission_required = 'inventory.change_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class ItemDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Artikel löschen"""
    model = Item
    template_name = 'inventory/item_confirm_delete.html'
    permission_required = 'inventory.delete_item'
    success_url = reverse_lazy('inventory:item_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Artikel "{self.object.name}" wurde erfolgreich gelöscht.')
        return super().delete(request, *args, **kwargs)


class ItemVariantDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detail-Ansicht einer Artikel-Variante"""
    model = ItemVariant
    template_name = 'inventory/variant_detail.html'
    permission_required = 'inventory.view_item'
    context_object_name = 'variant'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        variant = self.object
        
        # Bestandsinformationen hinzufügen
        stocks = Stock.objects.filter(item_variant=variant).select_related('location')
        context['stocks'] = stocks
        context['total_stock'] = sum(stock.quantity for stock in stocks)
        
        # Transaktionen hinzufügen
        context['recent_transactions'] = Transaction.objects.filter(
            item_variant=variant
        ).select_related('source', 'target', 'user').order_by('-date')[:10]
        
        context['can_edit_item'] = self.request.user.has_perm('inventory.change_item')
        context['can_add_transaction'] = self.request.user.has_perm('inventory.add_transaction')
        
        return context


class ItemVariantCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Eigene Seite zum Anlegen einer Variante (Alternative zum Modal)"""
    model = ItemVariant
    template_name = 'inventory/variant_form.html'
    permission_required = 'inventory.add_item'
    fields = ['parent_item', 'sku']  # variant_attributes separat

    def get_initial(self):
        initial = super().get_initial()
        parent_id = self.request.GET.get('parent')
        if parent_id:
            initial['parent_item'] = parent_id
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent = None
        parent_id = self.request.GET.get('parent') or self.request.POST.get('parent_item')
        if parent_id:
            try:
                parent = Item.objects.get(pk=parent_id)
            except Item.DoesNotExist:
                parent = None
        context['parent_item_obj'] = parent
        context['category_schema'] = parent.category.schema if parent and parent.category and parent.category.schema else {}
        return context

    def form_valid(self, form):
        variant_attributes = {}
        for key, value in self.request.POST.items():
            if key.startswith('attr_') and value:
                variant_attributes[key.replace('attr_', '')] = value
        form.instance.variant_attributes = variant_attributes
        # Mark parent as variant parent
        form.instance.parent_item.is_variant_parent = True
        form.instance.parent_item.save()
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.parent_item.get_absolute_url()


# ====================
# Bestand Views
# ====================

class StockListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Übersicht aller Bestände"""
    model = Stock
    template_name = 'inventory/stock_list.html'
    context_object_name = 'stocks'
    permission_required = 'inventory.view_stock'
    paginate_by = 50
    
    def get_queryset(self):
        qs = Stock.objects.select_related(
            'item', 'item_variant', 'item_variant__parent_item', 'location'
        ).filter(quantity__gt=0)
        # Sortiere primär nach Item-Name (falls vorhanden), sonst Parent-Item-Name für Varianten, dann Standort
        # Mit annotate für generischen Namen
        from django.db.models import Case, When, Value, CharField, F
        qs = qs.annotate(
            sort_name=Case(
                When(item__name__isnull=False, then=F('item__name')),
                When(item_variant__parent_item__name__isnull=False, then=F('item_variant__parent_item__name')),
                default=Value(''),
                output_field=CharField()
            )
        ).order_by('sort_name', 'location__name')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_categories'] = Category.objects.order_by('name')
        context['filter_locations'] = StorageLocation.objects.order_by('name')
        return context


# ====================
# Transaktion Views
# ====================

class TransactionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Übersicht aller Transaktionen"""
    model = Transaction
    template_name = 'inventory/transaction_list.html'
    context_object_name = 'transactions'
    permission_required = 'inventory.view_transaction'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Transaction.objects.select_related(
            'item', 'item_variant', 'item_variant__parent_item', 'source', 'target', 'user'
        ).order_by('-date')
        
        # Filter für Mitglieder: nur eigene Transaktionen anzeigen
        if (not self.request.user.has_perm('inventory.change_transaction') and 
            hasattr(self.request.user, 'member')):
            # Zeige nur Transaktionen, die das Mitglied betreffen
            member_location = StorageLocation.objects.filter(
                member=self.request.user.member
            ).first()
            if member_location:
                queryset = queryset.filter(
                    models.Q(source=member_location) | models.Q(target=member_location)
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_add_transaction'] = self.request.user.has_perm('inventory.add_transaction')
        return context


class TransactionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Erstellen einer neuen Transaktion mit smarterer UX"""
    model = Transaction
    form_class = ImprovedTransactionForm
    template_name = 'inventory/transaction_form.html'
    permission_required = 'inventory.add_transaction'
    
    def get_form_kwargs(self):
        """Übergabe des aktuellen Benutzers und optionaler Parameter an das Formular"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # Optionale Parameter aus URL
        location_id = self.request.GET.get('location')  # Quelle
        target_id = self.request.GET.get('target')      # Ziel explizit
        item_id = self.request.GET.get('item')
        variant_id = self.request.GET.get('item_variant')
        member_id = self.request.GET.get('member')
        trans_type = self.request.GET.get('type')
        
        if location_id:
            try:
                kwargs['initial_location'] = StorageLocation.objects.get(pk=location_id)
            except StorageLocation.DoesNotExist:
                pass
        if target_id:
            try:
                kwargs['initial_target'] = StorageLocation.objects.get(pk=target_id)
            except StorageLocation.DoesNotExist:
                pass
        
        if item_id:
            try:
                kwargs['initial_item'] = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                pass
        if variant_id:
            try:
                kwargs['initial_variant'] = ItemVariant.objects.get(pk=variant_id)
            except ItemVariant.DoesNotExist:
                pass

        # Falls Ausleihe über Mitglied (Weitere Ausleihe Button)
        if member_id and not target_id:
            from members.models import Member
            try:
                member = Member.objects.get(pk=member_id)
                # Wenn Member keinen Lagerplatz hat: automatisch anlegen (einfacher Flow)
                if not member.storage_location:
                    member.storage_location = StorageLocation.objects.create(
                        name=f"{member.name} {member.lastname}",
                        is_member=True
                    )
                    member.save()
                kwargs['initial_target'] = member.storage_location
            except Member.DoesNotExist:
                pass

        if trans_type:
            kwargs['initial_transaction_type'] = trans_type
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Zusätzliche Kontext-Daten für die Vorlage
        location_id = self.request.GET.get('location')
        target_id = self.request.GET.get('target')
        item_id = self.request.GET.get('item')
        variant_id = self.request.GET.get('item_variant')
        member_id = self.request.GET.get('member')
        trans_type = self.request.GET.get('type')
        
        if location_id:
            try:
                context['initial_location'] = StorageLocation.objects.get(pk=location_id)
            except StorageLocation.DoesNotExist:
                pass
        if target_id:
            try:
                context['initial_target'] = StorageLocation.objects.get(pk=target_id)
            except StorageLocation.DoesNotExist:
                pass
        
        if item_id:
            try:
                context['initial_item'] = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                pass
        if variant_id:
            try:
                context['initial_variant'] = ItemVariant.objects.get(pk=variant_id)
            except ItemVariant.DoesNotExist:
                pass
        if member_id:
            context['member_id'] = member_id
        if trans_type:
            context['initial_transaction_type'] = trans_type
        
        return context
    
    def get_success_url(self):
        return reverse('inventory:transaction_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Speichern der Transaktion mit Benutzer-Information"""
        form.instance.user = self.request.user
        
        # Erfolgsmeldung vorbereiten
        transaction_type_dict = dict(Transaction.TRANSACTION_TYPES)
        type_name = transaction_type_dict.get(form.instance.transaction_type, 'Transaktion')
        
        messages.success(
            self.request,
            f'{type_name} für "{form.instance.get_item_name()}" wurde erfolgreich erstellt.'
        )
        
        return super().form_valid(form)


class TransactionDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detail-Ansicht einer Transaktion"""
    model = Transaction
    template_name = 'inventory/transaction_detail.html'
    permission_required = 'inventory.view_transaction'


# ====================
# Spezielle Views für Mitglieder
# ====================

class MemberLoanListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Übersicht der eigenen Ausleihen für Mitglieder"""
    model = Transaction
    template_name = 'inventory/member_loans.html'
    context_object_name = 'loans'
    
    def test_func(self):
        # Nur für Benutzer, die ein verknüpftes Mitglied haben
        return hasattr(self.request.user, 'member')
    
    def get_queryset(self):
        if not hasattr(self.request.user, 'member'):
            return Transaction.objects.none()
        
        member_location = StorageLocation.objects.filter(
            member=self.request.user.member
        ).first()
        
        if not member_location:
            return Transaction.objects.none()
        
        # Finde alle LOAN-Transaktionen zum Mitglied, die noch nicht zurückgegeben wurden
        # Alle LOAN-Transaktionen (Item oder Variante) zum Mitglied
        loans = Transaction.objects.filter(
            transaction_type='LOAN',
            target=member_location
        ).select_related('item', 'item_variant', 'item_variant__parent_item', 'source')
        # Herausfiltern der bereits zurückgegebenen (RETURN) für dasselbe Item/Variante
        returned_item_ids = Transaction.objects.filter(
            transaction_type='RETURN',
            source=member_location,
            item__isnull=False
        ).values_list('item_id', flat=True)
        returned_variant_ids = Transaction.objects.filter(
            transaction_type='RETURN',
            source=member_location,
            item_variant__isnull=False
        ).values_list('item_variant_id', flat=True)
        loans = loans.exclude(
            models.Q(item_id__in=returned_item_ids) | models.Q(item_variant_id__in=returned_variant_ids)
        )
        
        return loans


# ====================
# Dashboard / Home View
# ====================

class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard für Inventar-Übersicht"""
    template_name = 'inventory/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.has_perm('inventory.view_item'):
            context['total_items'] = Item.objects.count()
            context['total_categories'] = Category.objects.count()
        
        if self.request.user.has_perm('inventory.view_stock'):
            context['total_locations'] = StorageLocation.objects.count()
            context['total_stock_value'] = Stock.objects.aggregate(
                total=models.Sum('quantity')
            )['total'] or 0
        
        if self.request.user.has_perm('inventory.view_transaction'):
            context['recent_transactions'] = Transaction.objects.select_related(
                'item', 'item_variant', 'item_variant__parent_item', 'source', 'target', 'user'
            ).order_by('-date')[:5]
        
        # Für Mitglieder: eigene Ausleihen
        if hasattr(self.request.user, 'member'):
            member_location = StorageLocation.objects.filter(
                member=self.request.user.member
            ).first()
            if member_location:
                context['my_loans'] = Stock.objects.filter(
                    location=member_location,
                    quantity__gt=0
                ).select_related('item', 'item_variant', 'item_variant__parent_item')[:5]
        
        return context


############################ API (Legacy Notice) ################################
# The DRF viewsets previously defined here (ItemViewSet, CategoryViewSet) have
# been moved to `inventory.api.viewsets`.
# This section intentionally left without DRF classes to avoid duplication.
# Remove this notice once all templates/refs are updated.


# ====================
# Kategorien Views
# ====================

class CategoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Übersicht aller Kategorien"""
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    permission_required = 'inventory.view_category'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_add_category'] = self.request.user.has_perm('inventory.add_category')
        return context


class CategoryDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detail-Ansicht einer Kategorie"""
    model = Category
    template_name = 'inventory/category_detail.html'
    permission_required = 'inventory.view_category'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.item_set.all()
        context['can_edit'] = self.request.user.has_perm('inventory.change_category')
        context['can_delete'] = self.request.user.has_perm('inventory.delete_category')
        return context


class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Erstellen einer neuen Kategorie"""
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form_dynamic.html'
    permission_required = 'inventory.add_category'
    
    def get_success_url(self):
        return reverse('inventory:category_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Kategorie "{form.instance.name}" wurde erfolgreich erstellt.')
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Bearbeiten einer Kategorie"""
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form_dynamic.html'
    permission_required = 'inventory.change_category'
    
    def get_success_url(self):
        return reverse('inventory:category_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Kategorie "{form.instance.name}" wurde erfolgreich aktualisiert.')
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Löschen einer Kategorie"""
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    permission_required = 'inventory.delete_category'
    success_url = reverse_lazy('inventory:category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        # Check if category has any items
        context['related_items'] = category.item_set.all()
        context['items_count'] = category.item_set.count()
        return context
    
    def delete(self, request, *args, **kwargs):
        from django.db.models.deletion import ProtectedError
        from django.http import HttpResponseRedirect
        
        category = self.get_object()
        
        try:
            category_name = category.name
            result = super().delete(request, *args, **kwargs)
            messages.success(request, f'Kategorie "{category_name}" wurde erfolgreich gelöscht.')
            return result
        except ProtectedError as e:
            # Get related items
            related_items = category.item_set.all()
            items_list = ', '.join([item.name for item in related_items[:5]])  # Show first 5 items
            if related_items.count() > 5:
                items_list += f' und {related_items.count() - 5} weitere'
            
            messages.error(
                request, 
                f'Kategorie "{category.name}" kann nicht gelöscht werden, da sie noch von '
                f'{related_items.count()} Artikel(n) verwendet wird: {items_list}. '
                f'Bitte ändern Sie zuerst die Kategorie dieser Artikel oder löschen Sie die Artikel.'
            )
            return HttpResponseRedirect(reverse('inventory:category_detail', kwargs={'pk': category.pk}))


# ====================
# Lagerorte Views
# ====================

class StorageLocationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Übersicht aller Lagerorte mit hierarchischer Sortierung"""
    model = StorageLocation
    template_name = 'inventory/location_list.html'
    context_object_name = 'locations'
    permission_required = 'inventory.view_storagelocation'
    paginate_by = 50  # Mehr anzeigen für bessere Hierarchie-Übersicht
    
    def get_queryset(self):
        """Sortiert hierarchisch: zuerst Hauptlagerorte, dann deren Kinder"""
        # Alle Lagerorte mit ihren Beziehungen laden
        all_locations = StorageLocation.objects.select_related('member', 'parent').prefetch_related('children')
        
        # Hierarchische Sortierung
        sorted_locations = []
        
        # Zuerst alle Hauptlagerorte (ohne Parent)
        root_locations = all_locations.filter(parent__isnull=True).order_by('name')
        
        def add_location_with_children(location, locations_list):
            locations_list.append(location)
            # Kinder rekursiv hinzufügen
            children = location.children.all().order_by('name')
            for child in children:
                add_location_with_children(child, locations_list)
        
        for root in root_locations:
            add_location_with_children(root, sorted_locations)
        
        return sorted_locations
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_add_location'] = self.request.user.has_perm('inventory.add_storagelocation')
        
        # Statistiken hinzufügen
        total_locations = StorageLocation.objects.count()
        member_locations = StorageLocation.objects.filter(is_member=True).count()
        context['stats'] = {
            'total': total_locations,
            'member_locations': member_locations,
            'standard_locations': total_locations - member_locations,
        }
        return context


class StorageLocationDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detail-Ansicht eines Lagerortes"""
    model = StorageLocation
    template_name = 'inventory/location_detail.html'
    permission_required = 'inventory.view_storagelocation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stocks'] = self.object.stock_set.select_related('item', 'item_variant', 'item_variant__parent_item').filter(quantity__gt=0)
        context['assigned_members'] = self.object.assigned_members.all() if hasattr(self.object, 'assigned_members') else []
        context['can_edit'] = self.request.user.has_perm('inventory.change_storagelocation')
        context['can_delete'] = self.request.user.has_perm('inventory.delete_storagelocation')
        return context


class StorageLocationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Erstellen eines neuen Lagerortes"""
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/location_form.html'
    permission_required = 'inventory.add_storagelocation'
    
    def get_initial(self):
        """Setze übergeordneten Lagerort aus URL-Parameter"""
        initial = super().get_initial()
        parent_id = self.request.GET.get('parent')
        if parent_id:
            try:
                parent = StorageLocation.objects.get(pk=parent_id)
                initial['parent'] = parent
            except StorageLocation.DoesNotExist:
                pass
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent_id = self.request.GET.get('parent')
        if parent_id:
            try:
                context['parent_location'] = StorageLocation.objects.get(pk=parent_id)
            except StorageLocation.DoesNotExist:
                pass
        return context
    
    def get_success_url(self):
        return reverse('inventory:location_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Lagerort "{form.instance.name}" wurde erfolgreich erstellt.')
        return super().form_valid(form)


class StorageLocationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Bearbeiten eines Lagerortes"""
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/location_form.html'
    permission_required = 'inventory.change_storagelocation'
    
    def get_success_url(self):
        return reverse('inventory:location_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Lagerort "{form.instance.name}" wurde erfolgreich aktualisiert.')
        return super().form_valid(form)


class CategoryBrowserView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Interaktiver Kategorie-Browser mit AJAX-basierter Artikel-Anzeige"""
    template_name = 'inventory/category_browser.html'
    permission_required = 'inventory.view_category'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Kategorie-Browser'
        return context


class StorageLocationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Löschen eines Lagerortes"""
    model = StorageLocation
    template_name = 'inventory/location_confirm_delete.html'
    permission_required = 'inventory.delete_storagelocation'
    success_url = reverse_lazy('inventory:location_list')
    
    def delete(self, request, *args, **kwargs):
        location = self.get_object()
        messages.success(request, f'Lagerort "{location.name}" wurde erfolgreich gelöscht.')
        return super().delete(request, *args, **kwargs)


# ====================
# AJAX Views für Smart Transaktionen
# ====================

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Q


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





class ImprovedTransactionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Improved Transaction Create View with Select2 widgets and smart filtering
    """
    model = Transaction
    form_class = ImprovedTransactionForm
    template_name = 'inventory/transaction_form.html'
    permission_required = 'inventory.add_transaction'
    success_url = reverse_lazy('inventory:transaction_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # Get initial values from URL parameters
        initial_location_id = self.request.GET.get('source')
        initial_target_id = self.request.GET.get('target')
        initial_item_id = self.request.GET.get('item')
        initial_variant_id = self.request.GET.get('item_variant')
        initial_type = self.request.GET.get('type')
        initial_member_id = self.request.GET.get('member')
        
        if initial_location_id:
            try:
                kwargs['initial_location'] = StorageLocation.objects.get(id=initial_location_id)
            except StorageLocation.DoesNotExist:
                pass
        
        if initial_target_id:
            try:
                kwargs['initial_target'] = StorageLocation.objects.get(id=initial_target_id)
            except StorageLocation.DoesNotExist:
                pass
        
        if initial_item_id:
            try:
                kwargs['initial_item'] = Item.objects.get(id=initial_item_id)
            except Item.DoesNotExist:
                pass
        
        if initial_variant_id:
            try:
                kwargs['initial_variant'] = ItemVariant.objects.get(id=initial_variant_id)
            except ItemVariant.DoesNotExist:
                pass
        
        if initial_type:
            kwargs['initial_transaction_type'] = initial_type
        
        if initial_member_id:
            try:
                kwargs['initial_member'] = Member.objects.get(id=initial_member_id)
            except Member.DoesNotExist:
                pass
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add initial context for template
        initial_location_id = self.request.GET.get('source')
        initial_item_id = self.request.GET.get('item')
        initial_member_id = self.request.GET.get('member')
        
        if initial_location_id:
            try:
                context['initial_location'] = StorageLocation.objects.get(id=initial_location_id)
            except StorageLocation.DoesNotExist:
                pass
        
        if initial_item_id:
            try:
                context['initial_item'] = Item.objects.get(id=initial_item_id)
            except Item.DoesNotExist:
                pass
        
        if initial_member_id:
            try:
                context['initial_member'] = Member.objects.get(id=initial_member_id)
            except Member.DoesNotExist:
                pass
        
        return context
    
    def form_valid(self, form):
        transaction = form.save(commit=False)
        transaction.created_by = self.request.user
        transaction.save()
        
        # Process the transaction (update stock)
        transaction.process()
        
        # Show success message
        item_name = transaction.item.name if transaction.item else str(transaction.item_variant)
        messages.success(
            self.request,
            f'Transaktion "{transaction.get_transaction_type_display()}" für '
            f'"{item_name}" wurde erfolgreich ausgeführt.'
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            'Es gab Fehler beim Erstellen der Transaktion. Bitte überprüfen Sie Ihre Eingaben.'
        )
        return super().form_invalid(form)
