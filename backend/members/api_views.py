from django.http import HttpResponse
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, renderer_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Member, Parent, Status, Group, Event, EventType, Attachment
from .api_serializers import (
    MemberListSerializer, MemberDetailSerializer, MemberCreateUpdateSerializer,
    ParentSerializer, StatusSerializer, GroupSerializer,
    EventSerializer, EventTypeSerializer, AttachmentSerializer
)
from .resources import MemberResource


class PassthroughRenderer(BaseRenderer):
    """
    Return data as-is. View should supply a Response.
    """
    media_type = '*/*'
    format = 'binary'
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


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
    filterset_fields = ['status', 'group', 'canSwimm', 'gender']
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
        from django.db.models import Count, Avg, Min, Max
        from datetime import date

        qs = self.queryset
        total = qs.count()

        # Gender distribution
        gender_counts = {g: 0 for g in ['male', 'female', 'diverse', '']}
        for row in qs.values('gender').annotate(count=Count('id')):
            gender_counts[row['gender'] or ''] = row['count']

        # Status distribution
        by_status = []
        for status_obj in Status.objects.all():
            count = qs.filter(status=status_obj).count()
            by_status.append({'name': status_obj.name, 'color': status_obj.color, 'count': count})
        no_status_count = qs.filter(status__isnull=True).count()
        if no_status_count:
            by_status.append({'name': 'Kein Status', 'color': '#aaaaaa', 'count': no_status_count})

        # Group distribution
        by_group = []
        for group_obj in Group.objects.all():
            count = qs.filter(group=group_obj).count()
            by_group.append({'name': group_obj.name, 'count': count})
        no_group_count = qs.filter(group__isnull=True).count()
        if no_group_count:
            by_group.append({'name': 'Keine Gruppe', 'count': no_group_count})

        # Age statistics
        today = date.today()
        ages = []
        for birthday in qs.filter(birthday__isnull=False).values_list('birthday', flat=True):
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            ages.append(age)

        age_stats = {}
        if ages:
            age_stats = {
                'avg': round(sum(ages) / len(ages), 1),
                'min': min(ages),
                'max': max(ages),
            }
            # Age buckets: one bucket per year
            from collections import Counter
            age_counter = Counter(ages)
            buckets = [{'label': str(age), 'count': count} for age, count in sorted(age_counter.items())]
            age_stats['buckets'] = buckets

        # Swim capability
        can_swim = qs.filter(canSwimm=True).count()

        return Response({
            'total': total,
            'gender': {
                'male': gender_counts.get('male', 0),
                'female': gender_counts.get('female', 0),
                'diverse': gender_counts.get('diverse', 0),
                'unknown': gender_counts.get('', 0),
            },
            'by_status': by_status,
            'by_group': by_group,
            'age': age_stats,
            'can_swim': can_swim,
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

    @extend_schema(
        summary="Get member's attachments",
        description="Get all attachments associated with this member"
    )
    @action(detail=True, methods=['get'])
    def attachments(self, request, pk=None):
        from django.contrib.contenttypes.models import ContentType
        member = self.get_object()
        content_type = ContentType.objects.get_for_model(Member)
        attachments = Attachment.objects.filter(
            content_type=content_type,
            object_id=member.id
        ).order_by('-uploaded_at')
        serializer = AttachmentSerializer(attachments, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Export members to Excel",
        description="Export all members to an Excel file (.xlsx format)"
    )
    @action(detail=False, methods=['get'], url_path='export-excel', renderer_classes=[PassthroughRenderer])
    def export_excel(self, request):
        """Export all members to Excel file with JWT authentication"""
        # Check permission
        if not request.user.has_perm('members.view_member'):
            return Response({'error': 'Keine Berechtigung für Mitglieder-Export'}, status=403)
        
        # Use import_export to generate Excel file
        member_resource = MemberResource()
        dataset = member_resource.export(queryset=self.queryset)
        
        # Generate Excel file
        excel_data = dataset.xlsx
        
        # Create HTTP response with Excel file
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="members.xlsx"'
        
        return response


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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['member', 'type']
    search_fields = ['member__name', 'member__lastname', 'notes', 'type__name']
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


@extend_schema_view(
    list=extend_schema(summary="List all attachments", description="Get a paginated list of all attachments"),
    retrieve=extend_schema(summary="Get attachment details"),
    create=extend_schema(summary="Create new attachment"),
    update=extend_schema(summary="Update attachment"),
    partial_update=extend_schema(summary="Partially update attachment"),
    destroy=extend_schema(summary="Delete attachment")
)
class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all().order_by('-uploaded_at')
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['content_type', 'object_id']
    ordering_fields = ['uploaded_at', 'name']
    ordering = ['-uploaded_at']

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @extend_schema(
        summary="Download attachment",
        description="Download the attachment file"
    )
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        from django.http import FileResponse
        attachment = self.get_object()
        if attachment.file:
            response = FileResponse(attachment.file.open('rb'))
            response['Content-Disposition'] = f'attachment; filename="{attachment.name}"'
            return response
        return Response({"detail": "No file attached"}, status=404)
