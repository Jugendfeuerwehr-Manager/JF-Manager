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
    
    def get_ordering(self):
        """
        Get the field to order by from the request's query parameters.
        Default to sorting by lastname if no sort parameter is provided.
        """
        default_order = 'lastname'
        ordering = self.request.GET.get('sort', default_order)
        
        # Check if we're sorting in reverse order (field starts with '-')
        if ordering.startswith('-'):
            self.sort_direction = 'desc'
            self.sort_field = ordering[1:]  # Remove the '-' prefix
        else:
            self.sort_direction = 'asc'
            self.sort_field = ordering
            
        return ordering

    def get_queryset(self, **kwargs):
        """Get a queryset of all members, ordered by the specified field"""
        ordering = self.get_ordering()
        return get_members_list().order_by(ordering)

    def get_context_data(self, **kwargs):
        context = super(MemberTableView, self).get_context_data(**kwargs)
        
        # Apply ordering and filtering to the queryset
        queryset = self.get_queryset(**kwargs)
        filter = MemberFilter(self.request.GET, queryset=queryset)
        filter.form.helper = MemberTableFilterFormHelper()
        
        # Configure the table with pagination
        table = MemberTable(filter.qs)
        RequestConfig(self.request, paginate={"per_page": 50}).configure(table)
        
        # Add everything to the context
        context['filter'] = filter
        context['table'] = table
        context['members'] = filter.qs  # Use filtered queryset for both views
        context['sort_field'] = getattr(self, 'sort_field', 'lastname')
        context['sort_direction'] = getattr(self, 'sort_direction', 'asc')
        
        return context