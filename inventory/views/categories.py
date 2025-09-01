from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from inventory.forms import CategoryForm
from inventory.models import Category


class CategoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    permission_required = 'inventory.view_category'
    paginate_by = 20

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['can_add_category'] = self.request.user.has_perm('inventory.add_category')
        return context


class CategoryDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Category
    template_name = 'inventory/category_detail.html'
    permission_required = 'inventory.view_category'

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.item_set.all()
        perms = self.request.user
        context['can_edit'] = perms.has_perm('inventory.change_category')
        context['can_delete'] = perms.has_perm('inventory.delete_category')
        return context


class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form_dynamic.html'
    permission_required = 'inventory.add_category'

    def get_success_url(self):  # pragma: no cover
        return reverse('inventory:category_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):  # pragma: no cover
        messages.success(self.request, f'Kategorie "{form.instance.name}" wurde erfolgreich erstellt.')
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form_dynamic.html'
    permission_required = 'inventory.change_category'

    def get_success_url(self):  # pragma: no cover
        return reverse('inventory:category_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):  # pragma: no cover
        messages.success(self.request, f'Kategorie "{form.instance.name}" wurde erfolgreich aktualisiert.')
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    permission_required = 'inventory.delete_category'
    success_url = reverse_lazy('inventory:category_list')

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        context['related_items'] = category.item_set.all()
        context['items_count'] = category.item_set.count()
        return context

    def delete(self, request, *args, **kwargs):  # pragma: no cover
        from django.db.models.deletion import ProtectedError
        from django.http import HttpResponseRedirect
        category = self.get_object()
        try:
            category_name = category.name
            result = super().delete(request, *args, **kwargs)
            messages.success(request, f'Kategorie "{category_name}" wurde erfolgreich gelöscht.')
            return result
        except ProtectedError:
            related_items = category.item_set.all()
            items_list = ', '.join([item.name for item in related_items[:5]])
            if related_items.count() > 5:
                items_list += f' und {related_items.count() - 5} weitere'
            messages.error(
                request,
                f'Kategorie "{category.name}" kann nicht gelöscht werden, da sie noch von '
                f'{related_items.count()} Artikel(n) verwendet wird: {items_list}. Bitte ändern Sie zuerst die Kategorie dieser Artikel oder löschen Sie die Artikel.'
            )
            return HttpResponseRedirect(reverse('inventory:category_detail', kwargs={'pk': category.pk}))


class CategoryBrowserView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'inventory/category_browser.html'
    permission_required = 'inventory.view_category'

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Kategorie-Browser'
        return context
