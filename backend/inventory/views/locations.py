from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from inventory.forms import StorageLocationForm
from inventory.models import StorageLocation


class StorageLocationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = StorageLocation
    template_name = 'inventory/location_list.html'
    context_object_name = 'locations'
    permission_required = 'inventory.view_storagelocation'
    paginate_by = 50

    def get_queryset(self):  # pragma: no cover
        all_locations = StorageLocation.objects.select_related('member', 'parent').prefetch_related('children')
        sorted_locations = []
        root_locations = all_locations.filter(parent__isnull=True).order_by('name')

        def add_location_with_children(location, locations_list):
            locations_list.append(location)
            children = location.children.all().order_by('name')
            for child in children:
                add_location_with_children(child, locations_list)

        for root in root_locations:
            add_location_with_children(root, sorted_locations)
        return sorted_locations

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['can_add_location'] = self.request.user.has_perm('inventory.add_storagelocation')
        total_locations = StorageLocation.objects.count()
        member_locations = StorageLocation.objects.filter(is_member=True).count()
        context['stats'] = {
            'total': total_locations,
            'member_locations': member_locations,
            'standard_locations': total_locations - member_locations,
        }
        return context


class StorageLocationDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = StorageLocation
    template_name = 'inventory/location_detail.html'
    permission_required = 'inventory.view_storagelocation'

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['stocks'] = self.object.stock_set.select_related('item', 'item_variant', 'item_variant__parent_item').filter(quantity__gt=0)
        context['assigned_members'] = self.object.assigned_members.all() if hasattr(self.object, 'assigned_members') else []
        perms = self.request.user
        context['can_edit'] = perms.has_perm('inventory.change_storagelocation')
        context['can_delete'] = perms.has_perm('inventory.delete_storagelocation')
        return context


class StorageLocationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/location_form.html'
    permission_required = 'inventory.add_storagelocation'

    def get_initial(self):  # pragma: no cover
        initial = super().get_initial()
        parent_id = self.request.GET.get('parent')
        if parent_id:
            parent = StorageLocation.objects.filter(pk=parent_id).first()
            if parent:
                initial['parent'] = parent
        return initial

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        parent_id = self.request.GET.get('parent')
        if parent_id:
            parent = StorageLocation.objects.filter(pk=parent_id).first()
            if parent:
                context['parent_location'] = parent
        return context

    def get_success_url(self):  # pragma: no cover
        return reverse('inventory:location_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):  # pragma: no cover
        messages.success(self.request, f'Lagerort "{form.instance.name}" wurde erfolgreich erstellt.')
        return super().form_valid(form)


class StorageLocationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = StorageLocation
    form_class = StorageLocationForm
    template_name = 'inventory/location_form.html'
    permission_required = 'inventory.change_storagelocation'

    def get_success_url(self):  # pragma: no cover
        return reverse('inventory:location_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):  # pragma: no cover
        messages.success(self.request, f'Lagerort "{form.instance.name}" wurde erfolgreich aktualisiert.')
        return super().form_valid(form)


class StorageLocationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = StorageLocation
    template_name = 'inventory/location_confirm_delete.html'
    permission_required = 'inventory.delete_storagelocation'
    success_url = reverse_lazy('inventory:location_list')

    def delete(self, request, *args, **kwargs):  # pragma: no cover
        location = self.get_object()
        messages.success(request, f'Lagerort "{location.name}" wurde erfolgreich gelöscht.')
        return super().delete(request, *args, **kwargs)
