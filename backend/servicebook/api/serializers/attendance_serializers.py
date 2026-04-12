"""Attendance serializers for creating and managing attendance records."""
from django.db import transaction
from rest_framework import serializers

from members.models import Member
from servicebook.models import Attendance, Service


class AttendanceSerializer(serializers.ModelSerializer):
    """Standard attendance serializer with member details."""
    person_name = serializers.CharField(source='person.get_full_name', read_only=True)
    person_details = serializers.SerializerMethodField()
    service_topic = serializers.CharField(source='service.topic', read_only=True)
    service_date = serializers.DateTimeField(source='service.start', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id',
            'person',
            'person_name',
            'person_details',
            'service',
            'service_topic',
            'service_date',
            'state',
            'state_display',
        ]

    def get_person_details(self, obj):
        """Get detailed person information."""
        if obj.person:
            return {
                'id': obj.person.id,
                'name': obj.person.name,
                'lastname': obj.person.lastname,
                'full_name': obj.person.get_full_name(),
            }
        return None


class AttendanceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating attendance records."""

    class Meta:
        model = Attendance
        fields = ['person', 'service', 'state']

    def validate(self, data):
        """Validate that attendance record doesn't already exist."""
        person = data.get('person')
        service = data.get('service')

        if person and service:
            # Check if attendance already exists
            existing = Attendance.objects.filter(person=person, service=service).first()
            if existing:
                raise serializers.ValidationError(
                    'Attendance record already exists for this member and service.'
                )

        return data


class AttendanceBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating attendance records for a service."""
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    attendances = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )

    def validate_attendances(self, value):
        """Validate attendance data structure."""
        for item in value:
            if 'person_id' not in item:
                raise serializers.ValidationError('Each attendance must have person_id')
            if 'state' not in item:
                raise serializers.ValidationError('Each attendance must have state')
            if item['state'] not in ['A', 'E', 'F', None]:
                raise serializers.ValidationError('Invalid state value')
        return value

    def save(self):
        """Bulk update or create attendance records with atomic transaction."""
        service = self.validated_data['service']
        attendances_data = self.validated_data['attendances']

        created = []
        updated = []
        deleted = []

        with transaction.atomic():
            # First, clean up any duplicate records for this service
            self._cleanup_duplicates(service)

            for att_data in attendances_data:
                person_id = att_data['person_id']
                state = att_data['state']

                try:
                    person = Member.objects.get(pk=person_id)
                except Member.DoesNotExist:
                    continue

                # If state is None, delete the attendance record
                if state is None:
                    deleted_count, _ = Attendance.objects.filter(
                        person=person,
                        service=service
                    ).delete()
                    if deleted_count > 0:
                        deleted.append(person_id)
                    continue

                # Use update_or_create to handle both creation and updates atomically
                attendance, was_created = Attendance.objects.update_or_create(
                    person=person,
                    service=service,
                    defaults={'state': state}
                )

                if was_created:
                    created.append(attendance)
                else:
                    updated.append(attendance)

        return {
            'created': len(created),
            'updated': len(updated),
            'deleted': len(deleted),
            'total': len(created) + len(updated)
        }

    def _cleanup_duplicates(self, service):
        """Remove duplicate attendance records for a service, keeping the most recent."""
        from django.db.models import Count

        # Find duplicates
        duplicates = (
            Attendance.objects.filter(service=service)
            .values('person', 'service')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        for dup in duplicates:
            # Get all attendance records for this person/service combination
            records = Attendance.objects.filter(
                person_id=dup['person'],
                service_id=dup['service']
            ).order_by('-id')

            # Keep the first (most recent) record, delete the rest
            records_to_delete = records[1:]
            for record in records_to_delete:
                record.delete()
