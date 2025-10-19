"""
Serializers for Qualifications API with computed fields and list/detail variants
"""
from rest_framework import serializers
from qualifications.models import QualificationType, Qualification, SpecialTaskType, SpecialTask
from members.models import Member
from members.api_serializers import AttachmentSerializer
from users.models import CustomUser


class QualificationTypeSerializer(serializers.ModelSerializer):
    """Full serializer for QualificationType"""
    
    class Meta:
        model = QualificationType
        fields = ['id', 'name', 'expires', 'validity_period', 'description']


class QualificationTypeListSerializer(serializers.ModelSerializer):
    """Minimal serializer for dropdown/list views"""
    
    class Meta:
        model = QualificationType
        fields = ['id', 'name', 'expires']


class QualificationListSerializer(serializers.ModelSerializer):
    """Serializer for qualification list view (minimal fields)"""
    
    type_name = serializers.CharField(source='type.name', read_only=True)
    person_name = serializers.CharField(source='get_person_name', read_only=True)
    is_expired = serializers.SerializerMethodField()
    expires_soon = serializers.SerializerMethodField()
    status_class = serializers.CharField(source='get_status_class', read_only=True)
    
    class Meta:
        model = Qualification
        fields = [
            'id',
            'type',
            'type_name',
            'person_name',
            'date_acquired',
            'date_expires',
            'is_expired',
            'expires_soon',
            'status_class',
            'issued_by'
        ]
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_expires_soon(self, obj):
        return obj.expires_soon()


class QualificationDetailSerializer(serializers.ModelSerializer):
    """Serializer for qualification detail view (all fields)"""
    
    type_name = serializers.CharField(source='type.name', read_only=True)
    type_details = QualificationTypeSerializer(source='type', read_only=True)
    user_name = serializers.SerializerMethodField()
    member_name = serializers.SerializerMethodField()
    person_name = serializers.CharField(source='get_person_name', read_only=True)
    is_expired = serializers.SerializerMethodField()
    expires_soon = serializers.SerializerMethodField()
    status_class = serializers.CharField(source='get_status_class', read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Qualification
        fields = [
            'id',
            'type',
            'type_name',
            'type_details',
            'user',
            'user_name',
            'member',
            'member_name',
            'person_name',
            'date_acquired',
            'date_expires',
            'issued_by',
            'note',
            'is_expired',
            'expires_soon',
            'status_class',
            'attachments'
        ]
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_expires_soon(self, obj):
        return obj.expires_soon()
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None
    
    def get_member_name(self, obj):
        return obj.member.get_full_name() if obj.member else None


class QualificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating qualifications"""
    
    class Meta:
        model = Qualification
        fields = [
            'id',  # Include id so frontend gets it after creation
            'type',
            'user',
            'member',
            'date_acquired',
            'date_expires',
            'issued_by',
            'note'
        ]
    
    def validate(self, data):
        """Validate that exactly one of user or member is provided"""
        user = data.get('user')
        member = data.get('member')
        
        if not user and not member:
            raise serializers.ValidationError(
                'Either user or member must be provided'
            )
        
        if user and member:
            raise serializers.ValidationError(
                'Only one of user or member can be provided, not both'
            )
        
        return data


class SpecialTaskTypeSerializer(serializers.ModelSerializer):
    """Serializer for SpecialTaskType"""
    
    class Meta:
        model = SpecialTaskType
        fields = ['id', 'name', 'description']


class SpecialTaskListSerializer(serializers.ModelSerializer):
    """Serializer for special task list view"""
    
    task_name = serializers.CharField(source='task.name', read_only=True)
    person_name = serializers.CharField(source='get_person_name', read_only=True)
    is_active = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    status_class = serializers.CharField(source='get_status_class', read_only=True)
    
    class Meta:
        model = SpecialTask
        fields = [
            'id',
            'task',
            'task_name',
            'person_name',
            'start_date',
            'end_date',
            'is_active',
            'duration_days',
            'status_class'
        ]
    
    def get_is_active(self, obj):
        return obj.is_active()
    
    def get_duration_days(self, obj):
        return obj.get_duration_days()


class SpecialTaskDetailSerializer(serializers.ModelSerializer):
    """Serializer for special task detail view"""
    
    task_name = serializers.CharField(source='task.name', read_only=True)
    task_details = SpecialTaskTypeSerializer(source='task', read_only=True)
    user_name = serializers.SerializerMethodField()
    member_name = serializers.SerializerMethodField()
    person_name = serializers.CharField(source='get_person_name', read_only=True)
    is_active = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    status_class = serializers.CharField(source='get_status_class', read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = SpecialTask
        fields = [
            'id',
            'task',
            'task_name',
            'task_details',
            'user',
            'user_name',
            'member',
            'member_name',
            'person_name',
            'start_date',
            'end_date',
            'note',
            'is_active',
            'duration_days',
            'status_class',
            'attachments'
        ]
    
    def get_is_active(self, obj):
        return obj.is_active()
    
    def get_duration_days(self, obj):
        return obj.get_duration_days()
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None
    
    def get_member_name(self, obj):
        return obj.member.get_full_name() if obj.member else None


class SpecialTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating special tasks"""
    
    # Make both fields optional but require at least one
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False,
        allow_null=True
    )
    member = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = SpecialTask
        fields = [
            'id',  # Include id so frontend gets it after creation
            'task',
            'user',
            'member',
            'start_date',
            'end_date',
            'note'
        ]
    
    def validate(self, data):
        """Validate constraints"""
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"SpecialTaskCreateSerializer.validate() called with data: {data}")
        logger.info(f"  user field: {data.get('user')} (type: {type(data.get('user'))})")
        logger.info(f"  member field: {data.get('member')} (type: {type(data.get('member'))})")
        
        # Get values, treating None as falsy
        user = data.get('user')
        member = data.get('member')
        
        # Check if neither is provided (both are None or missing)
        if user is None and member is None:
            logger.error("Validation failed: Neither user nor member provided")
            raise serializers.ValidationError({
                'non_field_errors': ['Entweder Benutzer oder Mitglied muss ausgewählt werden.']
            })
        
        # Check if both are provided (both have values)
        if user is not None and member is not None:
            logger.error(f"Validation failed: Both user ({user}) and member ({member}) provided")
            raise serializers.ValidationError({
                'non_field_errors': ['Nur Benutzer oder Mitglied kann ausgewählt werden, nicht beide.']
            })
        
        # Validate dates
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if end_date and start_date and end_date < start_date:
            logger.error(f"Validation failed: end_date ({end_date}) before start_date ({start_date})")
            raise serializers.ValidationError({
                'end_date': 'Enddatum kann nicht vor Startdatum liegen.'
            })
        
        logger.info("Validation passed successfully")
        return data
