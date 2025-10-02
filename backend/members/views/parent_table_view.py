from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from django_tables2 import RequestConfig

from members.filters import ParentFilter
from members.models import Parent
from members.selectors import get_parent_list
from members.tables import ParentTable
from members.views.parent_table_filter_form_helper import ParentTableFilterFormHelper


class ParentTableView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'parents_table.html'
    permission_required = 'members.view_parent'

    def get_queryset(self, **kwargs):
        return get_parent_list()

    def get_context_data(self, **kwargs):
        context = super(ParentTableView, self).get_context_data(**kwargs)
        filter = ParentFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter.form.helper = ParentTableFilterFormHelper()
        table = ParentTable(filter.qs)
        RequestConfig(self.request).configure(table)
        context['filter'] = filter
        context['table'] = table
        context['parents'] = get_parent_list()
        context['allmail'] = ','.join(Parent.objects.values_list('email', flat=True)) + ','.join(Parent.objects.values_list('email2', flat=True))
        return context