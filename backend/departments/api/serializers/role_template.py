from rest_framework import serializers

from departments.delegation import delegation_approved
from departments.models import RoleTemplate


class RoleTemplateReadSerializer(serializers.ModelSerializer):
    delegation_approved = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()

    class Meta:
        model = RoleTemplate
        fields = [
            "id",
            "key",
            "name",
            "description",
            "template_version",
            "scope",
            "is_delegable",
            "delegation_approved",
            "is_archived",
            "group",
        ]

    def get_delegation_approved(self, obj):
        return delegation_approved(obj)

    def get_group(self, obj):
        if obj.group_id is None:
            return None
        return {"id": obj.group_id, "name": obj.group.name}
