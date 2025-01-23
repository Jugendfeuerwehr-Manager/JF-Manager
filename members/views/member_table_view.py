from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from django_tables2 import RequestConfig

from members.filters import MemberFilter
from members.selectors import get_members_list
from members.tables import MemberTable
from members.views.member_table_filter_form_helper import MemberTableFilterFormHelper


class MemberTableView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'members_table.html'
    permission_required = 'members.view_member'

    def get_queryset(self, **kwargs):
        return get_members_list()

    def get_context_data(self, **kwargs):
        context = super(MemberTableView, self).get_context_data(**kwargs)
        filter = MemberFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter.form.helper = MemberTableFilterFormHelper()
        table = MemberTable(filter.qs)
        RequestConfig(self.request).configure(table)
        context['filter'] = filter
        context['table'] = table
        context['members'] = get_members_list()
        return context