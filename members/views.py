from django_tables2 import SingleTableMixin
from django_filters.views import FilterView
from .forms import MemberFilter, MemberFilterFormHelper

class MemberListView(SingleTableMixin, FilterView):
    model = Member
    table_class = MemberTable
    template_name = 'members/members_table.html'
    filterset_class = MemberFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'].form.helper = MemberFilterFormHelper()
        context['members'] = self.filterset.qs
        return context
