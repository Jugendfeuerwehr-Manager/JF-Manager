from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserInfoSerializer(serializers.ModelSerializer):
    """Complete user information including permissions"""
    permissions = serializers.SerializerMethodField()
    groups = GroupSerializer(many=True, read_only=True)
    avatar_url = serializers.SerializerMethodField()
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'mobile_phone', 'street', 'zip_code', 'city',
            'is_staff', 'is_active', 'is_superuser',
            'date_joined', 'last_login',
            'avatar', 'avatar_url',
            'dsgvo_internal', 'dsgvo_external',
            'groups', 'permissions'
        ]
        read_only_fields = [
            'id', 'username', 'date_joined', 'last_login', 
            'is_staff', 'is_superuser', 'groups', 'permissions'
        ]

    def get_permissions(self, obj):
        """Get all permissions (user + group permissions)"""
        if obj.is_superuser:
            return ['superuser']
        
        # Get direct permissions
        user_perms = obj.user_permissions.values_list('codename', flat=True)
        # Get group permissions
        group_perms = Permission.objects.filter(group__user=obj).values_list('codename', flat=True)
        
        all_perms = set(list(user_perms) + list(group_perms))
        return list(all_perms)

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for lists"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'is_staff', 'is_active', 'avatar_url'
        ]
        read_only_fields = ['id', 'username']

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None
