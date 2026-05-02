import django_filters

from departments.models import Department


class DepartmentFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Department
        fields = ["is_active"]
