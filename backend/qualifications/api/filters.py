"""
Custom filters for Qualifications API.
Provides status-based filtering for qualifications and special tasks.
"""

from datetime import date, timedelta

from django.db import models
from django_filters import rest_framework as filters

from qualifications.models import Qualification, SpecialTask


class QualificationFilter(filters.FilterSet):
    """Custom filters for qualifications"""

    status = filters.ChoiceFilter(
        method="filter_status",
        choices=[
            ("all", "All"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("expiring", "Expiring Soon"),
        ],
    )

    class Meta:
        model = Qualification
        fields = ["member", "user", "type", "status"]

    def filter_status(self, queryset, name, value):
        """Filter by qualification status"""
        today = date.today()
        soon_threshold = today + timedelta(days=30)

        if value == "expired":
            return queryset.filter(date_expires__lt=today)
        elif value == "expiring":
            return queryset.filter(date_expires__gte=today, date_expires__lte=soon_threshold)
        elif value == "active":
            return queryset.filter(models.Q(date_expires__isnull=True) | models.Q(date_expires__gt=today))

        return queryset


class SpecialTaskFilter(filters.FilterSet):
    """Custom filters for special tasks"""

    status = filters.ChoiceFilter(
        method="filter_status",
        choices=[
            ("all", "All"),
            ("active", "Active"),
            ("ended", "Ended"),
        ],
    )

    class Meta:
        model = SpecialTask
        fields = ["member", "user", "task", "status"]

    def filter_status(self, queryset, name, value):
        """Filter by task status"""
        today = date.today()

        if value == "active":
            return queryset.filter(models.Q(end_date__isnull=True) | models.Q(end_date__gt=today))
        elif value == "ended":
            return queryset.filter(end_date__lte=today)

        return queryset
