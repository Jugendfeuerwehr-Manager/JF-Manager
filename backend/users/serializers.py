from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer für Benutzerinformationen"""
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
            'mobile_phone',
            'street',
            'zip_code',
            'city',
            'avatar',
            'date_joined',
            'last_login',
            'is_active',
            'is_staff',
        ]
        read_only_fields = [
            'id',
            'username',
            'date_joined',
            'last_login',
            'is_staff',
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer für Benutzerprofil-Updates"""
    
    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'phone',
            'mobile_phone',
            'street',
            'zip_code',
            'city',
            'avatar',
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer für Passwort-Änderung"""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Die neuen Passwörter stimmen nicht überein.")
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Das alte Passwort ist inkorrekt.")
        return value