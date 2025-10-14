"""Attendance viewsets for managing attendance records."""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache

from servicebook.models import Attendance
from servicebook.selectors import get_attandance_list
from ..serializers import (
    AttendanceSerializer,
    AttendanceCreateSerializer,
    AttendanceBulkUpdateSerializer,
)


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing attendance records.
    
    Provides:
    - Standard CRUD operations
    - Filtering by person, service, state
    - Search by person name
    - Bulk update endpoint for efficient attendance marking
    """
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    queryset = Attendance.objects.all()  # Base queryset for router registration
    serializer_class = AttendanceSerializer  # Default serializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['person', 'service', 'state']
    search_fields = ['person__name', 'person__lastname']
    ordering_fields = ['state', 'id', 'service__start']
    ordering = ['-service__start']
    
    def get_queryset(self):
        """Get attendance list with optimized queries."""
        return get_attandance_list().select_related('person', 'service')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AttendanceCreateSerializer
        elif self.action == 'bulk_update':
            return AttendanceBulkUpdateSerializer
        return AttendanceSerializer
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Bulk update or create attendance records for a service.
        
        Expected payload:
        {
            "service": <service_id>,
            "attendances": [
                {"person_id": 1, "state": "A"},
                {"person_id": 2, "state": "E"},
                {"person_id": 3, "state": "F"}
            ]
        }
        
        Returns:
        {
            "created": <count>,
            "updated": <count>,
            "total": <count>
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        # Clear attendance cache
        cache.delete('attendance_over_time_data')
        
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def by_member(self, request):
        """
        Get attendance records for a specific member.
        
        Query params:
        - member_id: ID of the member
        - limit: Number of records to return (default: 50)
        """
        member_id = request.query_params.get('member_id')
        if not member_id:
            return Response(
                {'error': 'member_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        limit = int(request.query_params.get('limit', 50))
        
        attendances = self.get_queryset().filter(person_id=member_id).order_by('-service__start')[:limit]
        serializer = self.get_serializer(attendances, many=True)
        
        # Calculate summary statistics
        total = attendances.count()
        present = attendances.filter(state='A').count()
        excused = attendances.filter(state='E').count()
        absent = attendances.filter(state='F').count()
        
        return Response({
            'attendances': serializer.data,
            'summary': {
                'total': total,
                'present': present,
                'excused': excused,
                'absent': absent,
            }
        })
    
    def perform_create(self, serializer):
        """Handle attendance creation and clear cache."""
        attendance = serializer.save()
        cache.delete('attendance_over_time_data')
        return attendance
    
    def perform_update(self, serializer):
        """Handle attendance update and clear cache."""
        attendance = serializer.save()
        cache.delete('attendance_over_time_data')
        return attendance
    
    def perform_destroy(self, instance):
        """Handle attendance deletion and clear cache."""
        instance.delete()
        cache.delete('attendance_over_time_data')
