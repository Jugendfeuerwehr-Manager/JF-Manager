from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Attachment, Event, EventType, Group, Member, Parent, Status

User = get_user_model()


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ["id", "name", "color"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "department"]


class ParentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = Parent
        fields = [
            "id",
            "name",
            "lastname",
            "full_name",
            "email",
            "email2",
            "phone",
            "mobile",
            "street",
            "zip_code",
            "city",
            "notes",
            "children",
        ]
        read_only_fields = ["id", "full_name"]


class MemberListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""

    status = StatusSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    parents = ParentSerializer(source="parent_set", many=True, read_only=True)
    age = serializers.IntegerField(source="get_age", read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    avatar_url = serializers.SerializerMethodField()
    has_alert = serializers.SerializerMethodField()
    department_ids = serializers.PrimaryKeyRelatedField(source="departments", many=True, read_only=True)

    class Meta:
        model = Member
        fields = [
            "id",
            "name",
            "lastname",
            "full_name",
            "birthday",
            "age",
            "email",
            "phone",
            "mobile",
            "city",
            "joined",
            "gender",
            "status",
            "group",
            "parents",
            "avatar_url",
            "has_alert",
            "department_ids",
        ]
        read_only_fields = ["id", "age", "full_name", "parents", "avatar_url", "has_alert"]

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_has_alert(self, obj):
        try:
            from servicebook.selectors import get_attandance_alert_by_member

            return get_attandance_alert_by_member(obj)
        except Exception:
            return False


class MemberDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single member views"""

    status = StatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source="status", write_only=True, required=False
    )
    group = GroupSerializer(read_only=True)
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), source="group", write_only=True, required=False
    )
    parents = ParentSerializer(source="parent_set", many=True, read_only=True)
    age = serializers.IntegerField(source="get_age", read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id",
            "name",
            "lastname",
            "full_name",
            "birthday",
            "age",
            "email",
            "street",
            "zip_code",
            "city",
            "phone",
            "mobile",
            "notes",
            "joined",
            "identityCardNumber",
            "canSwimm",
            "gender",
            "status",
            "status_id",
            "group",
            "group_id",
            "storage_location",
            "parents",
            "avatar",
            "avatar_url",
            "departments",
        ]
        read_only_fields = ["id", "age", "full_name", "parents", "avatar_url"]

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class MemberCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for create/update operations"""

    def validate(self, attrs):
        attrs = super().validate(attrs)

        group = attrs.get("group", serializers.empty)
        departments = attrs.get("departments", serializers.empty)

        if group is serializers.empty:
            group = self.instance.group if self.instance else None

        if departments is serializers.empty:
            if self.instance:
                departments = list(self.instance.departments.all())
            else:
                departments = []

        if group and group.department_id is not None:
            department_ids = {department.id for department in departments}

            if group.department_id not in department_ids:
                if "group" in attrs:
                    raise serializers.ValidationError(
                        {"group": "Die gewählte Gruppe gehört nicht zu den zugewiesenen Abteilungen."}
                    )

                # Existing group no longer matches after department move:
                # auto-clear it to keep member visible/manageable.
                attrs["group"] = None

        return attrs

    class Meta:
        model = Member
        fields = [
            "id",
            "name",
            "lastname",
            "birthday",
            "email",
            "street",
            "zip_code",
            "city",
            "phone",
            "mobile",
            "notes",
            "joined",
            "identityCardNumber",
            "canSwimm",
            "gender",
            "status",
            "group",
            "storage_location",
            "avatar",
            "departments",
        ]
        read_only_fields = ["id"]


class EventTypeSerializer(serializers.ModelSerializer):
    event_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = EventType
        fields = ["id", "name", "department", "event_count"]


class EventSerializer(serializers.ModelSerializer):
    event_type = EventTypeSerializer(source="type", read_only=True)
    type_id = serializers.PrimaryKeyRelatedField(
        queryset=EventType.objects.all(), source="type", write_only=True, required=False
    )
    member_name = serializers.CharField(source="member.get_full_name", read_only=True)

    class Meta:
        model = Event
        fields = ["id", "member", "member_name", "type", "event_type", "type_id", "datetime", "notes"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        member = attrs.get("member", self.instance.member if self.instance else None)
        event_type = attrs.get("type", self.instance.type if self.instance else None)

        if not member or not event_type or event_type.department_id is None:
            return attrs

        member_department_ids = set(member.departments.values_list("id", flat=True))
        if event_type.department_id not in member_department_ids:
            raise serializers.ValidationError(
                {"type": "Der gewählte Ereignistyp gehört nicht zu den Abteilungen des Mitglieds."}
            )

        return attrs


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    mime_type = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "name",
            "file",
            "file_url",
            "description",
            "uploaded_at",
            "content_type",
            "object_id",
            "mime_type",
            "file_size",
        ]
        # Generic relation is resolved by the target endpoint (e.g. /training/blocks/{id}/attachments/)
        # and must not be required from API clients.
        read_only_fields = [
            "id",
            "uploaded_at",
            "file_url",
            "mime_type",
            "file_size",
            "content_type",
            "object_id",
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None

    def get_mime_type(self, obj):
        if obj.file:
            import mimetypes

            mime_type, _ = mimetypes.guess_type(obj.file.name)
            return mime_type
        return None

    def get_file_size(self, obj):
        if obj.file:
            return obj.file.size
        return None
