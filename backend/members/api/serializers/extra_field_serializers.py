import re

from django.utils.text import slugify
from rest_framework import serializers

from members.models import Member, MemberFieldDefinition
from members.services.extra_fields import clean_definition_options

GERMAN = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})


def _key_from_label(label):
    base = re.sub(r"[^a-z0-9_]", "_", slugify(label.translate(GERMAN)).replace("-", "_")).strip("_")[:40] or "feld"
    if not base[0].isalpha():
        base = f"f_{base}"
    key, counter = base, 2
    while MemberFieldDefinition.objects.filter(key=key).exists():
        key = f"{base}_{counter}"
        counter += 1
    return key


class MemberFieldDefinitionSerializer(serializers.ModelSerializer):
    key = serializers.RegexField(r"^[a-z][a-z0-9_]{0,49}$", required=False, max_length=50)
    in_use = serializers.SerializerMethodField()

    class Meta:
        model = MemberFieldDefinition
        fields = [
            "id",
            "department",
            "key",
            "label",
            "field_type",
            "options",
            "help_text",
            "position",
            "active",
            "in_use",
        ]
        read_only_fields = ["id", "in_use"]

    def get_in_use(self, definition):
        return Member.objects.filter(extra_fields__has_key=definition.key).exists()

    def validate(self, attrs):
        if self.instance is not None:
            # Stored values are keyed by it, and their meaning depends on the type.
            for name in ("key", "field_type", "department"):
                if name in attrs and attrs[name] != getattr(self.instance, name):
                    raise serializers.ValidationError({name: "Lässt sich nach dem Anlegen nicht mehr ändern."})
        field_type = attrs.get("field_type", getattr(self.instance, "field_type", MemberFieldDefinition.FieldType.TEXT))
        if "options" in attrs or "field_type" in attrs:
            options, error = clean_definition_options(field_type, attrs.get("options", []))
            if error:
                raise serializers.ValidationError({"options": error})
            attrs["options"] = options
        if self.instance is None and not attrs.get("key"):
            attrs["key"] = _key_from_label(attrs.get("label", ""))
        if self.instance is None and MemberFieldDefinition.objects.filter(key=attrs["key"]).exists():
            raise serializers.ValidationError({"key": "Diese Kennung ist schon vergeben."})
        return attrs
