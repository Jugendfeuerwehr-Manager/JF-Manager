from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Member, Parent, Status, Group, Event, EventType, Attachment


User = get_user_model()


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ['id', 'name', 'color']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class ParentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Parent
        fields = [
            'id', 'name', 'lastname', 'full_name', 'email', 'email2',
            'phone', 'mobile', 'street', 'zip_code', 'city', 'notes', 'children'
        ]
        read_only_fields = ['id', 'full_name']


class MemberListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    status = StatusSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    parents = ParentSerializer(source='parent_set', many=True, read_only=True)
    age = serializers.IntegerField(source='get_age', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Member
        fields = [
            'id', 'name', 'lastname', 'full_name', 'birthday', 'age',
            'email', 'phone', 'mobile', 'city', 'joined',
            'status', 'group', 'parents', 'avatar_url'
        ]
        read_only_fields = ['id', 'age', 'full_name', 'parents', 'avatar_url']

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class MemberDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single member views"""
    status = StatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source='status', write_only=True, required=False
    )
    group = GroupSerializer(read_only=True)
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), source='group', write_only=True, required=False
    )
    parents = ParentSerializer(source='parent_set', many=True, read_only=True)
    age = serializers.IntegerField(source='get_age', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Member
        fields = [
            'id', 'name', 'lastname', 'full_name', 'birthday', 'age',
            'email', 'street', 'zip_code', 'city', 'phone', 'mobile',
            'notes', 'joined', 'identityCardNumber', 'canSwimm',
            'status', 'status_id', 'group', 'group_id', 
            'storage_location', 'parents', 'avatar', 'avatar_url'
        ]
        read_only_fields = ['id', 'age', 'full_name', 'parents', 'avatar_url']

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class MemberCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for create/update operations"""
    
    class Meta:
        model = Member
        fields = [
            'id', 'name', 'lastname', 'birthday',
            'email', 'street', 'zip_code', 'city', 'phone', 'mobile',
            'notes', 'joined', 'identityCardNumber', 'canSwimm',
            'status', 'group', 'storage_location', 'avatar'
        ]
        read_only_fields = ['id']


class EventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventType
        fields = ['id', 'name']


class EventSerializer(serializers.ModelSerializer):
    event_type = EventTypeSerializer(source='type', read_only=True)
    type_id = serializers.PrimaryKeyRelatedField(
        queryset=EventType.objects.all(), source='type', write_only=True, required=False
    )
    member_name = serializers.CharField(source='member.get_full_name', read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'member', 'member_name', 'type', 'event_type', 'type_id',
            'datetime', 'notes'
        ]
        read_only_fields = ['id']


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'file', 'file_url', 'description', 'uploaded_at',
            'content_type', 'object_id'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
