"""Django-filter FilterSets for Training API."""

from django_filters import rest_framework as filters

from training.models import LibraryBlock, TrainingBlock, TrainingSession


class TrainingSessionFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="date", lookup_expr="lte")
    group = filters.NumberFilter(field_name="groups__id")
    has_recurrence = filters.BooleanFilter(method="filter_has_recurrence")

    class Meta:
        model = TrainingSession
        fields = ["date_from", "date_to", "group", "has_recurrence"]

    def filter_has_recurrence(self, queryset, name, value):
        if value:
            return queryset.exclude(recurrence_rule__isnull=True)
        return queryset.filter(recurrence_rule__isnull=True)


class TrainingBlockFilter(filters.FilterSet):
    session = filters.NumberFilter(field_name="session__id")
    group = filters.NumberFilter(field_name="groups__id")

    class Meta:
        model = TrainingBlock
        fields = ["session", "group"]


class LibraryBlockFilter(filters.FilterSet):
    category = filters.NumberFilter(field_name="category__id")
    tag = filters.NumberFilter(field_name="tags__id")
    is_public = filters.BooleanFilter()
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = LibraryBlock
        fields = ["category", "tag", "is_public"]

    def filter_search(self, queryset, name, value):
        from django.db.models import Q

        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))
