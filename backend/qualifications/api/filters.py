"""
Custom filters for Qualifications API.
Provides status-based filtering for qualifications and special tasks.
"""

from datetime import date, timedelta

from django.db import models
from django.db.models import Exists, OuterRef, Q
from django_filters import rest_framework as filters

from qualifications.models import Qualification, SpecialTask

EXPIRY_WINDOWS = (30, 60, 90)


def current_qualifications(queryset):
    """Drop qualifications superseded by a later one of the same type for the same person (renewals)."""
    newer = (
        Qualification.objects.filter(type=OuterRef("type"))
        .filter(Q(member_id=OuterRef("member_id")) | Q(user_id=OuterRef("user_id")))
        .filter(
            Q(date_acquired__gt=OuterRef("date_acquired"))
            | Q(date_acquired=OuterRef("date_acquired"), id__gt=OuterRef("id"))
        )
    )
    return queryset.filter(~Exists(newer))


def expiring_within(queryset, days, today=None):
    """Qualifications that are still valid today but expire within the given number of days."""
    today = today or date.today()
    return queryset.filter(date_expires__gte=today, date_expires__lte=today + timedelta(days=days))


def without_evidence(queryset):
    return queryset.filter(attachments__isnull=True)


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

    expiring_within = filters.ChoiceFilter(
        method="filter_expiring_within",
        choices=[(str(days), f"{days} days") for days in EXPIRY_WINDOWS],
    )
    without_evidence = filters.BooleanFilter(method="filter_without_evidence")
    current = filters.BooleanFilter(method="filter_current")

    class Meta:
        model = Qualification
        fields = ["member", "user", "type", "status"]

    def filter_expiring_within(self, queryset, name, value):
        return expiring_within(queryset, int(value))

    def filter_without_evidence(self, queryset, name, value):
        return without_evidence(queryset) if value else queryset

    def filter_current(self, queryset, name, value):
        return current_qualifications(queryset) if value else queryset

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
