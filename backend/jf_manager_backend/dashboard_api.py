"""
UX-01.1: one summary request for the dashboard instead of loading full lists to count them.

Each section reuses the list viewset of its module (permission check and get_queryset with the
same request), so counts follow exactly the rights and department scope of the list a tile links to.
A section the caller may not see is returned as null.
"""

from datetime import timedelta

from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from members.models import MemberListEntry
from orders.models import OrderItem
from qualifications.api.filters import EXPIRY_WINDOWS, current_qualifications, expiring_within, without_evidence

UPCOMING_SERVICE_DAYS = 14


def scoped_list_queryset(request, viewset_class):
    """The queryset the module's list endpoint would use for this request, or None without access."""
    view = viewset_class()
    view.request = request
    view.action = "list"
    view.args = ()
    view.kwargs = {}
    view.format_kwarg = None
    view.headers = {}
    try:
        view.check_permissions(request)
        return view.get_queryset()
    except (NotAuthenticated, PermissionDenied):
        return None


def members_section(qs):
    return {"total": qs.count()}


def parents_section(qs):
    return {"total": qs.count()}


def qualifications_section(qs):
    current = current_qualifications(qs)
    today = timezone.localdate()
    return {
        "expired": current.filter(date_expires__lt=today).count(),
        "expiring": {str(days): expiring_within(current, days, today).count() for days in EXPIRY_WINDOWS},
        "without_evidence": without_evidence(current).count(),
    }


def services_section(qs):
    now = timezone.now()
    upcoming = qs.filter(start__gte=now, start__lte=now + timedelta(days=UPCOMING_SERVICE_DAYS)).order_by("start")
    following = upcoming.first()
    return {
        "upcoming_days": UPCOMING_SERVICE_DAYS,
        "upcoming": upcoming.count(),
        "next": (
            {
                "id": following.id,
                "start": following.start,
                "topic": following.topic or "",
                "place": following.place or "",
            }
            if following
            else None
        ),
    }


def orders_section(qs):
    undelivered = OrderItem.objects.filter(order=OuterRef("pk"), delivered_date__isnull=True)
    return {"open": qs.filter(Exists(undelivered)).count()}


def lists_section(qs):
    unchecked = MemberListEntry.objects.filter(member_list=OuterRef("pk"), checked=False)
    return {"open": qs.filter(Exists(unchecked)).count()}


def sections():
    # Imported on use: the module viewsets import serializers that would otherwise form a cycle with urls.py.
    from members.api.viewsets import MemberListViewSet, MemberViewSet, ParentViewSet
    from orders.api.viewsets import OrderViewSet
    from qualifications.api.viewsets import QualificationViewSet
    from servicebook.api.viewsets import ServiceViewSet

    return {
        "members": (MemberViewSet, members_section),
        "parents": (ParentViewSet, parents_section),
        "qualifications": (QualificationViewSet, qualifications_section),
        "services": (ServiceViewSet, services_section),
        "orders": (OrderViewSet, orders_section),
        "lists": (MemberListViewSet, lists_section),
    }


class DashboardSummaryView(APIView):
    """GET /api/v1/dashboard/summary/: counts only, never person lists."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        summary = {}
        for key, (viewset_class, build) in sections().items():
            qs = scoped_list_queryset(request, viewset_class)
            summary[key] = None if qs is None else build(qs)
        return Response(summary)
