"""Service serializers with computed fields and attendance summaries."""

from django.db.models import Count
from rest_framework import serializers

from members.models import Member
from servicebook.models import Attendance, Service
from users.models import CustomUser


class OperationsManagerSerializer(serializers.ModelSerializer):
    """Minimal serializer for operations managers."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = CustomUser
        fields = ["id", "username", "full_name", "email"]


class AttendanceSummarySerializer(serializers.Serializer):
    """Serializer for attendance summary statistics."""

    present = serializers.IntegerField()
    excused = serializers.IntegerField()
    absent = serializers.IntegerField()
    total = serializers.IntegerField()


class ServiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for service lists with attendance summary."""

    operations_manager = OperationsManagerSerializer(many=True, read_only=True)
    operations_manager_ids = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source="operations_manager", many=True, write_only=True, required=False
    )

    # Attendance summary
    attendance_summary = serializers.SerializerMethodField()
    has_events = serializers.BooleanField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "start",
            "end",
            "place",
            "topic",
            "department",
            "training_session",
            "operations_manager",
            "operations_manager_ids",
            "attendance_summary",
            "has_events",
        ]

    def get_attendance_summary(self, obj):
        """Calculate attendance summary for this service."""
        # Try to use pre-calculated summary if available
        if hasattr(obj, "attendance_summary"):
            return {
                "present": obj.attendance_summary.get("A", 0),
                "excused": obj.attendance_summary.get("E", 0),
                "absent": obj.attendance_summary.get("F", 0),
                "total": sum(obj.attendance_summary.values()),
            }

        # Otherwise calculate from database
        attendance_counts = Attendance.objects.filter(service=obj).values("state").annotate(count=Count("id"))
        counts = {"A": 0, "E": 0, "F": 0}
        for item in attendance_counts:
            counts[item["state"]] = item["count"]

        return {
            "present": counts["A"],
            "excused": counts["E"],
            "absent": counts["F"],
            "total": sum(counts.values()),
        }


class AttendeeDetailSerializer(serializers.ModelSerializer):
    """Serializer for attendee information in service details."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ["id", "name", "lastname", "full_name", "status"]

    def get_status(self, obj):
        """Get attendance status for this member."""
        service = self.context.get("service")
        if service:
            attendance = Attendance.objects.filter(service=service, person=obj).first()
            if attendance:
                return attendance.state
        return None


class ServiceDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual service view."""

    operations_manager = OperationsManagerSerializer(many=True, read_only=True)
    operations_manager_ids = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source="operations_manager", many=True, write_only=True, required=False
    )

    # Attendance information
    attendance_summary = serializers.SerializerMethodField()
    attendees_with_status = serializers.SerializerMethodField()
    has_events = serializers.BooleanField(read_only=True)

    # Computed fields
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "start",
            "end",
            "place",
            "topic",
            "description",
            "events",
            "department",
            "training_session",
            "operations_manager",
            "operations_manager_ids",
            "attendance_summary",
            "attendees_with_status",
            "has_events",
            "duration_minutes",
        ]

    def get_attendance_summary(self, obj):
        """Calculate attendance summary."""
        attendance_counts = Attendance.objects.filter(service=obj).values("state").annotate(count=Count("id"))
        counts = {"A": 0, "E": 0, "F": 0}
        for item in attendance_counts:
            counts[item["state"]] = item["count"]

        return {
            "present": counts["A"],
            "excused": counts["E"],
            "absent": counts["F"],
            "total": sum(counts.values()),
        }

    def get_attendees_with_status(self, obj):
        """Get all attendees with their attendance status."""
        attendances = Attendance.objects.filter(service=obj).select_related("person")
        return [
            {
                "id": att.person.id,
                "name": att.person.name,
                "lastname": att.person.lastname,
                "full_name": att.person.get_full_name(),
                "state": att.state,
                "attendance_id": att.id,
            }
            for att in attendances
        ]

    def get_duration_minutes(self, obj):
        """Calculate service duration in minutes."""
        if obj.start and obj.end:
            delta = obj.end - obj.start
            return int(delta.total_seconds() / 60)
        return None


class ServiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new services."""

    operations_manager_ids = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source="operations_manager", many=True, required=False
    )

    class Meta:
        model = Service
        fields = [
            "start",
            "end",
            "place",
            "topic",
            "description",
            "events",
            "department",
            "operations_manager_ids",
        ]

    def validate(self, data):
        """Validate service data."""
        if data.get("start") and data.get("end") and data["end"] <= data["start"]:
            raise serializers.ValidationError({"end": "End time must be after start time."})
        return data


class ServiceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating services."""

    operations_manager_ids = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source="operations_manager", many=True, required=False
    )

    class Meta:
        model = Service
        fields = [
            "start",
            "end",
            "place",
            "topic",
            "description",
            "events",
            "department",
            "operations_manager_ids",
        ]

    def validate(self, data):
        """Validate service data."""
        start = data.get("start", self.instance.start if self.instance else None)
        end = data.get("end", self.instance.end if self.instance else None)

        if start and end and end <= start:
            raise serializers.ValidationError({"end": "End time must be after start time."})
        return data
