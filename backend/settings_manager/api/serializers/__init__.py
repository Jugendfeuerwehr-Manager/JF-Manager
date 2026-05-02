"""
Serializers for Settings API
"""

from rest_framework import serializers

from .email_template import (
    EmailTemplateCreateUpdateSerializer,
    EmailTemplateDetailSerializer,
    EmailTemplateListSerializer,
    EmailTemplatePreviewResponseSerializer,
    EmailTemplatePreviewSerializer,
)


class GeneralSettingsSerializer(serializers.Serializer):
    """Serializer for general settings"""

    title = serializers.CharField(
        max_length=200, required=False, allow_blank=True, help_text="Website title displayed in browser tab"
    )


class EmailSettingsSerializer(serializers.Serializer):
    """Serializer for email settings"""

    email_host = serializers.CharField(
        max_length=200, required=False, allow_blank=True, help_text="SMTP server hostname or IP address"
    )
    email_port = serializers.IntegerField(
        required=False, min_value=1, max_value=65535, help_text="SMTP server port (e.g., 587 for TLS, 465 for SSL)"
    )
    email_use_tls = serializers.BooleanField(required=False, help_text="Use TLS encryption for email connection")
    email_use_ssl = serializers.BooleanField(
        required=False, help_text="Use SSL encryption for email connection (not together with TLS)"
    )
    email_host_user = serializers.CharField(
        max_length=200, required=False, allow_blank=True, help_text="Username for SMTP authentication"
    )
    email_host_password = serializers.CharField(
        required=False, allow_blank=True, write_only=True, help_text="Password for SMTP authentication"
    )
    default_from_email = serializers.EmailField(
        required=False, allow_blank=True, help_text="Email address used as sender"
    )

    def validate(self, data):
        """Validate that TLS and SSL are not both enabled"""
        if data.get("email_use_tls") and data.get("email_use_ssl"):
            raise serializers.ValidationError("TLS and SSL cannot be enabled at the same time")
        return data


class MemberSettingsSerializer(serializers.Serializer):
    """Serializer for member settings"""

    alert_threshold = serializers.IntegerField(
        required=False, min_value=1, help_text="Threshold for absence alert (number of absences)"
    )
    alert_threshold_last_entries = serializers.IntegerField(
        required=False, min_value=1, help_text="Number of recent services to check for absences"
    )


class ServiceSettingsSerializer(serializers.Serializer):
    """Serializer for service settings"""

    service_start_time = serializers.TimeField(required=False, help_text="Default start time for new services")
    service_end_time = serializers.TimeField(required=False, help_text="Default end time for new services")

    def validate(self, data):
        """Validate that start time is before end time"""
        start_time = data.get("service_start_time")
        end_time = data.get("service_end_time")

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time")
        return data


class OrderSettingsSerializer(serializers.Serializer):
    """Serializer for order settings"""

    equipment_manager_email = serializers.EmailField(
        required=False, allow_blank=True, help_text="Equipment manager email address for order notifications"
    )


class AllSettingsSerializer(serializers.Serializer):
    """
    Combined serializer for all settings
    Used for GET /api/v1/settings/ to return all settings at once
    """

    general = GeneralSettingsSerializer(required=False)
    email = EmailSettingsSerializer(required=False)
    member = MemberSettingsSerializer(required=False)
    service = ServiceSettingsSerializer(required=False)
    order = OrderSettingsSerializer(required=False)


class CategorySettingsUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating a specific category's settings
    Used for PATCH/PUT to update settings by category
    """

    category = serializers.ChoiceField(
        choices=["general", "email", "member", "service", "order"],
        required=True,
        help_text="Settings category to update",
    )
    settings = serializers.DictField(required=True, help_text="Settings key-value pairs to update")


class UserPermissionsSerializer(serializers.Serializer):
    """
    Serializer for user's settings permissions
    Returns which categories the user can view/change
    """

    can_view_all = serializers.BooleanField()
    can_change_all = serializers.BooleanField()
    categories = serializers.DictField(child=serializers.DictField(child=serializers.BooleanField()))


__all__ = [
    "AllSettingsSerializer",
    "CategorySettingsUpdateSerializer",
    "EmailSettingsSerializer",
    "EmailTemplateCreateUpdateSerializer",
    "EmailTemplateDetailSerializer",
    "EmailTemplateListSerializer",
    "EmailTemplatePreviewResponseSerializer",
    "EmailTemplatePreviewSerializer",
    "GeneralSettingsSerializer",
    "MemberSettingsSerializer",
    "OrderSettingsSerializer",
    "ServiceSettingsSerializer",
    "UserPermissionsSerializer",
]
