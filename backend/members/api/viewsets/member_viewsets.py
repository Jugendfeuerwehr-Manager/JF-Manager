"""
MemberViewSet — CRUD + custom statistics/export actions.
"""
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response

from members.api_serializers import (
    AttachmentSerializer,
    EventSerializer,
    GroupSerializer,
    MemberCreateUpdateSerializer,
    MemberDetailSerializer,
    MemberListSerializer,
    ParentSerializer,
    StatusSerializer,
)
from members.models import Attachment, Event, Group, Member, Status
from members.resources import MemberResource


class PassthroughRenderer(BaseRenderer):
    """Return data as-is for binary responses."""
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
    retrieve=extend_schema(summary="Get member details"),
    create=extend_schema(summary="Create new member"),
    update=extend_schema(summary="Update member"),
    partial_update=extend_schema(summary="Partially update member"),
    destroy=extend_schema(summary="Delete member")
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
        description="Statistics about members: total, by gender, status, group, age, swim capability"
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        from collections import Counter
        from datetime import date

        from django.db.models import Count

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
            age_counter = Counter(ages)
            age_stats = {
                'avg': round(sum(ages) / len(ages), 1),
                'min': min(ages),
                'max': max(ages),
                'buckets': [{'label': str(age), 'count': count} for age, count in sorted(age_counter.items())],
            }

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
            'can_swim': qs.filter(canSwimm=True).count(),
        })

    @extend_schema(summary="Get member's parents")
    @action(detail=True, methods=['get'])
    def parents(self, request, pk=None):
        member = self.get_object()
        serializer = ParentSerializer(member.parent_set.all(), many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(summary="Get member's events")
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        member = self.get_object()
        events = Event.objects.filter(member=member).order_by('-datetime')
        serializer = EventSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(summary="Get member's attachments")
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

    @extend_schema(summary="Export members to Excel")
    @action(detail=False, methods=['get'], url_path='export-excel', renderer_classes=[PassthroughRenderer])
    def export_excel(self, request):
        if not request.user.has_perm('members.view_member'):
            return Response({'error': 'Keine Berechtigung für Mitglieder-Export'}, status=403)

        member_resource = MemberResource()
        dataset = member_resource.export(queryset=self.queryset)
        excel_data = dataset.xlsx

        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="members.xlsx"'
        return response
