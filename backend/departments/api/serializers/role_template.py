from rest_framework import serializers

from departments.models import RoleTemplate


class RoleTemplateReadSerializer(serializers.ModelSerializer):
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
            "is_archived",
            "group",
        ]

    def get_group(self, obj):
        if obj.group_id is None:
            return None
        return {"id": obj.group_id, "name": obj.group.name}
