import crispy_forms
from crispy_forms.layout import Submit, Layout

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, UpdateView, DeleteView, CreateView
from django_tables2 import RequestConfig
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication

from .serializers import ItemSerializer, CategorySerializer
from .filters import ItemFilter
from .forms import ItemForm, FormActionMixin
from .models import Item
from .tables import ItemTable
from .selectors import get_item_list, get_category_list


class ItemFilterFormHelper(crispy_forms.helper.FormHelper):
    form_method = 'GET'
    form_class = 'form-inline'
    layout = Layout(
        'category',
        'size',
        'identifier1',
        'identifier2',
        'rented_by',
        Submit('submit', 'Filtern')

    )

class ItemTableView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory_items.html'

    def get_queryset(self, **kwargs):
        return get_item_list()

    def get_context_data(self, **kwargs):
        context = super(ItemTableView, self).get_context_data(**kwargs)
        filter = ItemFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter.form.helper = ItemFilterFormHelper()
        table = ItemTable(filter.qs)
        RequestConfig(self.request).configure(table)
        context['filter'] = filter
        context['table'] = table
        context['items'] = get_item_list()

        return context




class ItemUpdateView(FormActionMixin, UpdateView):
    model = Item
    form_class = ItemForm
    template_name = 'inventory_item_edit.html'

    def get_success_url(self):
        return 'inventory:items'

    def form_valid(self, form):
        item = form.save(commit=False)
        item.save()
        return redirect('inventory:home')


    # def get_object(self, queryset=None):
    #
    #     return Department.objects.get(pk=self.kwargs['pk'])


class ItemDeleteView(DeleteView):
    model = Item
    template_name = 'item_confirm_delete.html'
    success_url = reverse_lazy('inventory:items')


class ItemCreateView(FormActionMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'inventory_item_edit.html'

    def get_success_url(self):
        return 'inventory:items'

    def form_valid(self, form):
        item = form.save(commit=False)
        item.save()
        return redirect('inventory:home')


############################ API ################################################

class ItemViewSet(viewsets.ModelViewSet):
    """
    API Endpoint that allows members to be viewed or edited.

    With the search parameter you can search for the barcode identifiers, the name and lastname of the rented_by person,
    and the category name.
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_item_list()
    serializer_class = ItemSerializer
    filterset_fields = '__all__'
    search_fields = ['rented_by__name', 'rented_by__lastname', 'category__name', 'identifier1', 'identifier2']

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API Endpoint that allows members to be viewed or edited
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_category_list()
    serializer_class = CategorySerializer
    filterset_fields = '__all__'
    search_fields = ['name']

