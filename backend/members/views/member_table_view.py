from datetime import date
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Q
from django_tables2 import RequestConfig

from members.filters import MemberFilter
from members.selectors import get_members_list
from members.tables import MemberTable
from members.views.member_table_filter_form_helper import MemberTableFilterFormHelper
from members.models import Member, Status
from servicebook.selectors import get_attandance_alert_by_member


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
        
        # Calculate statistics
        context['statistics'] = self.get_member_statistics(filter.qs)
        
        # Add everything to the context
        context['filter'] = filter
        context['table'] = table
        context['members'] = filter.qs  # Use filtered queryset for both views
        context['sort_field'] = getattr(self, 'sort_field', 'lastname')
        context['sort_direction'] = getattr(self, 'sort_direction', 'asc')
        
        return context

    def get_member_statistics(self, queryset):
        """Calculate member statistics for age and status"""
        statistics = {}
        
        # Status statistics
        status_stats = queryset.values('status__name', 'status__color').annotate(
            count=Count('id')
        ).order_by('status__name')
        
        statistics['status_counts'] = list(status_stats)
        statistics['total_members'] = queryset.count()
        
        # Attendance alert statistics
        members_with_alerts = 0
        for member in queryset:
            if get_attandance_alert_by_member(member):
                members_with_alerts += 1
        
        statistics['attendance_alerts'] = members_with_alerts
        
        # Age statistics
        members_with_birthday = queryset.filter(birthday__isnull=False)
        if members_with_birthday.exists():
            today = date.today()
            ages = []
            # Create age ranges for individual years from 8 to 18, plus under 8 and over 18
            age_ranges = {}
            for age in range(8, 19):  # 8 to 18 inclusive
                age_ranges[str(age)] = 0
            age_ranges['< 8'] = 0
            age_ranges['> 18'] = 0
            
            for member in members_with_birthday:
                age = member.get_age()
                ages.append(age)
                
                # Categorize age into ranges
                if age < 8:
                    age_ranges['< 8'] += 1
                elif age > 18:
                    age_ranges['> 18'] += 1
                else:
                    age_ranges[str(age)] += 1
            
            statistics['age_stats'] = {
                'average_age': round(sum(ages) / len(ages), 1) if ages else 0,
                'min_age': min(ages) if ages else 0,
                'max_age': max(ages) if ages else 0,
                'age_ranges': age_ranges,
                'members_with_birthday': len(ages),
                'members_without_birthday': queryset.count() - len(ages)
            }
        else:
            statistics['age_stats'] = {
                'average_age': 0,
                'min_age': 0,
                'max_age': 0,
                'age_ranges': {},
                'members_with_birthday': 0,
                'members_without_birthday': queryset.count()
            }
        
        return statistics