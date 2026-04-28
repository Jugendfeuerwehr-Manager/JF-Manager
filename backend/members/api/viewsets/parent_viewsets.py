"""
ParentViewSet — CRUD for member parents/guardians.
"""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from members.api_serializers import ParentSerializer
from members.models import Parent


@extend_schema_view(
    list=extend_schema(summary="List all parents"),
    retrieve=extend_schema(summary="Get parent details"),
    create=extend_schema(summary="Create new parent"),
    update=extend_schema(summary="Update parent"),
    partial_update=extend_schema(summary="Partially update parent"),
    destroy=extend_schema(summary="Delete parent")
)
class ParentViewSet(viewsets.ModelViewSet):
    queryset = Parent.objects.prefetch_related('children')
    serializer_class = ParentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = []
    search_fields = ['name', 'lastname', 'email', 'email2']
    ordering_fields = ['name', 'lastname']
    ordering = ['lastname', 'name']
