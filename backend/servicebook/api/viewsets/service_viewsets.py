"""Service viewsets with statistics and filtering."""
from django.core.cache import cache
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from servicebook.models import Attendance, Service
from servicebook.selectors import (
    get_attendance_over_time_data,
    get_services_with_attendance_summary,
    get_top_lists_by_state,
)

from ..serializers import (
    ServiceCreateSerializer,
    ServiceDetailSerializer,
    ServiceListSerializer,
    ServiceUpdateSerializer,
)


class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing services with attendance tracking.

    Provides:
    - Standard CRUD operations
    - Filtering by topic, place, date range, operations_manager
    - Search by topic, description, place
    - Statistics endpoints for attendance summaries
    """
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    queryset = Service.objects.all()  # Base queryset for router registration
    serializer_class = ServiceDetailSerializer  # Default serializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['topic', 'place', 'operations_manager', 'start', 'end']
    search_fields = ['topic', 'description', 'events', 'place']
    ordering_fields = ['start', 'end', 'topic']
    ordering = ['-start']

    def get_queryset(self):
        """Get services with optimized prefetch."""
        return get_services_with_attendance_summary()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ServiceListSerializer
        elif self.action == 'create':
            return ServiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ServiceUpdateSerializer
        return ServiceDetailSerializer

    def create(self, request, *args, **kwargs):
        """Create service and return detailed response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = self.perform_create(serializer)

        # Use DetailSerializer for response to include all fields including id
        detail_serializer = ServiceDetailSerializer(service)
        headers = self.get_success_headers(detail_serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get overall servicebook statistics.

        Returns:
        - Total services count
        - Recent services summary
        - Top attendance lists (most present, excused, absent)
        """
        services_count = Service.objects.count()
        recent_services = Service.objects.order_by('-start')[:5]

        # Get top lists
        top_present = get_top_lists_by_state('A', max_entries=7)
        top_excused = get_top_lists_by_state('E', max_entries=7)
        top_absent = get_top_lists_by_state('F', max_entries=7)

        return Response({
            'total_services': services_count,
            'recent_services': ServiceListSerializer(recent_services, many=True).data,
            'top_lists': {
                'most_present': list(top_present),
                'most_excused': list(top_excused),
                'most_absent': list(top_absent),
            }
        })

    @action(detail=False, methods=['get'])
    def attendance_chart(self, request):
        """
        Get attendance data for chart visualization.

        Returns time-series data of attendance across services.
        """
        chart_data = get_attendance_over_time_data()
        return Response(chart_data)

    @action(detail=True, methods=['get'])
    def attendance_summary(self, request, pk=None):
        """
        Get detailed attendance summary for a specific service.

        Returns:
        - Counts by state (A, E, F)
        - List of attendees with their status
        """
        service = self.get_object()

        # Get attendance summary
        attendance_counts = Attendance.objects.filter(service=service).values('state').annotate(count=Count('id'))
        counts = {'A': 0, 'E': 0, 'F': 0}
        for item in attendance_counts:
            counts[item['state']] = item['count']

        # Get all attendees with status
        attendances = Attendance.objects.filter(service=service).select_related('person')
        attendees = [
            {
                'id': att.person.id,
                'name': att.person.name,
                'lastname': att.person.lastname,
                'full_name': att.person.get_full_name(),
                'state': att.state,
                'state_display': att.get_state_display(),
                'attendance_id': att.id,
            }
            for att in attendances
        ]

        return Response({
            'summary': {
                'present': counts['A'],
                'excused': counts['E'],
                'absent': counts['F'],
                'total': sum(counts.values()),
            },
            'attendees': attendees,
        })

    def perform_create(self, serializer):
        """Handle service creation and clear cache."""
        service = serializer.save()
        # Clear attendance cache when new service is created
        cache.delete('attendance_over_time_data')
        return service

    def perform_update(self, serializer):
        """Handle service update and clear cache."""
        service = serializer.save()
        # Clear attendance cache when service is updated
        cache.delete('attendance_over_time_data')
        return service

    def perform_destroy(self, instance):
        """Handle service deletion and clear cache."""
        instance.delete()
        # Clear attendance cache when service is deleted
        cache.delete('attendance_over_time_data')
