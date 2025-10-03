from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Member, Parent, Status, Group, Event, EventType, Attachment
from .api_serializers import (
    MemberListSerializer, MemberDetailSerializer, MemberCreateUpdateSerializer,
    ParentSerializer, StatusSerializer, GroupSerializer,
    EventSerializer, EventTypeSerializer, AttachmentSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="List all members",
        description="Get a paginated list of all members with filtering and sorting",
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, description='Search by name, lastname, email'),
            OpenApiParameter('status', OpenApiTypes.INT, description='Filter by status ID'),
            OpenApiParameter('group', OpenApiTypes.INT, description='Filter by group ID'),
            OpenApiParameter('ordering', OpenApiTypes.STR, description='Order by: name, lastname, birthday, joined')
        ]
    ),
    retrieve=extend_schema(summary="Get member details", description="Get detailed information about a specific member"),
    create=extend_schema(summary="Create new member", description="Create a new member"),
    update=extend_schema(summary="Update member", description="Update all member fields"),
    partial_update=extend_schema(summary="Partially update member", description="Update specific member fields"),
    destroy=extend_schema(summary="Delete member", description="Delete a member")
)
class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.select_related('status', 'group', 'storage_location').prefetch_related('parent_set')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'group', 'canSwimm']
    search_fields = ['name', 'lastname', 'email', 'identityCardNumber']
    ordering_fields = ['name', 'lastname', 'birthday', 'joined']
    ordering = ['lastname', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return MemberListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return MemberCreateUpdateSerializer
        return MemberDetailSerializer

    @extend_schema(
        summary="Get member statistics",
        description="Get statistics about members (total, active, by status, etc.)"
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        total = self.queryset.count()
        by_status = {}
        for status_obj in Status.objects.all():
            by_status[status_obj.name] = self.queryset.filter(status=status_obj).count()
        
        return Response({
            'total': total,
            'by_status': by_status
        })

    @extend_schema(
        summary="Get member's parents",
        description="Get all parents associated with this member"
    )
    @action(detail=True, methods=['get'])
    def parents(self, request, pk=None):
        member = self.get_object()
        parents = member.parent_set.all()
        serializer = ParentSerializer(parents, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Get member's events",
        description="Get all events associated with this member"
    )
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        member = self.get_object()
        events = Event.objects.filter(member=member).order_by('-datetime')
        serializer = EventSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="List all parents", description="Get a paginated list of all parents"),
    retrieve=extend_schema(summary="Get parent details", description="Get detailed information about a specific parent"),
    create=extend_schema(summary="Create new parent", description="Create a new parent"),
    update=extend_schema(summary="Update parent", description="Update all parent fields"),
    partial_update=extend_schema(summary="Partially update parent", description="Update specific parent fields"),
    destroy=extend_schema(summary="Delete parent", description="Delete a parent")
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


@extend_schema_view(
    list=extend_schema(summary="List all statuses", description="Get all member statuses"),
    retrieve=extend_schema(summary="Get status details"),
    create=extend_schema(summary="Create new status"),
    update=extend_schema(summary="Update status"),
    partial_update=extend_schema(summary="Partially update status"),
    destroy=extend_schema(summary="Delete status")
)
class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['name']


@extend_schema_view(
    list=extend_schema(summary="List all groups", description="Get all member groups"),
    retrieve=extend_schema(summary="Get group details"),
    create=extend_schema(summary="Create new group"),
    update=extend_schema(summary="Update group"),
    partial_update=extend_schema(summary="Partially update group"),
    destroy=extend_schema(summary="Delete group")
)
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['name']


@extend_schema_view(
    list=extend_schema(summary="List all events", description="Get all member events"),
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
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['member', 'type']
    ordering_fields = ['datetime']
    ordering = ['-datetime']


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
