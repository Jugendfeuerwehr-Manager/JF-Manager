"""
EventViewSet and EventTypeViewSet — member lifecycle event tracking.
"""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from members.api_serializers import EventSerializer, EventTypeSerializer
from members.models import Event, EventType


@extend_schema_view(
    list=extend_schema(summary="List all event types"),
    retrieve=extend_schema(summary="Get event type details"),
    create=extend_schema(summary="Create new event type"),
    update=extend_schema(summary="Update event type"),
    partial_update=extend_schema(summary="Partially update event type"),
    destroy=extend_schema(summary="Delete event type")
)
class EventTypeViewSet(viewsets.ModelViewSet):
    queryset = EventType.objects.all()
    serializer_class = EventTypeSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['name']


@extend_schema_view(
    list=extend_schema(summary="List all events"),
    retrieve=extend_schema(summary="Get event details"),
    create=extend_schema(summary="Create new event"),
    update=extend_schema(summary="Update event"),
    partial_update=extend_schema(summary="Partially update event"),
    destroy=extend_schema(summary="Delete event")
)
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.select_related('member', 'type').order_by('-datetime')
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['member', 'type']
    search_fields = ['member__name', 'member__lastname', 'notes', 'type__name']
    ordering_fields = ['datetime']
    ordering = ['-datetime']
