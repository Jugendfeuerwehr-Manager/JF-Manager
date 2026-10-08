from rest_framework import serializers

from .models import Invitation


class InvitationSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    person_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = [
            "id",
            "kind",
            "parent",
            "member",
            "person_name",
            "email",
            "state",
            "created_at",
            "created_by_name",
            "sent_at",
            "expires_at",
            "accepted_at",
            "revoked_at",
        ]
        read_only_fields = fields

    def get_person_name(self, obj):
        return obj.record.get_full_name()

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username if obj.created_by else ""


class InvitationCreateSerializer(serializers.Serializer):
    parent = serializers.IntegerField(required=False)
    member = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if bool(attrs.get("parent")) == bool(attrs.get("member")):
            raise serializers.ValidationError("Genau einen Eltern- oder Mitgliedsdatensatz angeben.")
        return attrs


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(write_only=True, max_length=128)
    password_confirm = serializers.CharField(write_only=True, max_length=128)
    privacy_accepted = serializers.BooleanField()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Die Passwörter stimmen nicht überein."})
        if not attrs["privacy_accepted"]:
            raise serializers.ValidationError({"privacy_accepted": "Bitte den Datenschutzhinweis bestätigen."})
        return attrs
