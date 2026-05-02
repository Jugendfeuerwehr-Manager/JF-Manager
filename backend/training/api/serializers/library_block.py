"""Serializers for LibraryBlock, LibraryBlockCategory, LibraryBlockTag."""

from rest_framework import serializers

from training.models import LibraryBlock, LibraryBlockCategory, LibraryBlockTag, TrainingMedia


class LibraryBlockCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryBlockCategory
        fields = ["id", "name", "color", "icon"]


class LibraryBlockTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryBlockTag
        fields = ["id", "name"]


class TrainingMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = TrainingMedia
        fields = ["id", "url", "original_filename", "created_at"]

    def get_url(self, obj):
        if obj.file:
            return obj.file.url  # Relative path (e.g. /uploads/…); proxied by nginx/Vite
        return obj.url


class LibraryBlockListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_color = serializers.CharField(source="category.color", read_only=True)
    tags = LibraryBlockTagSerializer(many=True, read_only=True)
    usage_count = serializers.IntegerField(read_only=True, default=0)
    last_used_date = serializers.DateField(read_only=True, allow_null=True, default=None)

    class Meta:
        model = LibraryBlock
        fields = [
            "id",
            "export_uuid",
            "title",
            "description",
            "default_duration_minutes",
            "category",
            "category_name",
            "category_color",
            "tags",
            "color",
            "is_public",
            "created_at",
            "usage_count",
            "last_used_date",
        ]


class LibraryBlockDetailSerializer(serializers.ModelSerializer):
    category = LibraryBlockCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=LibraryBlockCategory.objects.all(),
        source="category",
        write_only=True,
        allow_null=True,
        required=False,
    )
    tags = LibraryBlockTagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=LibraryBlockTag.objects.all(),
        source="tags",
        write_only=True,
        many=True,
        required=False,
    )
    media = serializers.SerializerMethodField()

    class Meta:
        model = LibraryBlock
        fields = [
            "id",
            "export_uuid",
            "title",
            "description",
            "content",
            "default_duration_minutes",
            "category",
            "category_id",
            "tags",
            "tag_ids",
            "color",
            "nextcloud_folder_url",
            "is_public",
            "source_instance_url",
            "created_by",
            "created_at",
            "updated_at",
            "media",
        ]
        read_only_fields = ["export_uuid", "created_by", "created_at", "updated_at"]

    def get_media(self, obj):
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(obj)
        qs = TrainingMedia.objects.filter(content_type=ct, object_id=obj.pk)
        return TrainingMediaSerializer(qs, many=True, context=self.context).data

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.tags.set(tags)
        return instance

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        instance = super().create(validated_data)
        instance.tags.set(tags)
        return instance


class LibraryBlockExportSerializer(serializers.ModelSerializer):
    """Federation-ready export format."""

    category = serializers.CharField(source="category.name", default=None)
    tags = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()

    class Meta:
        model = LibraryBlock
        fields = [
            "export_uuid",
            "title",
            "description",
            "content",
            "default_duration_minutes",
            "category",
            "tags",
            "color",
            "nextcloud_folder_url",
        ]

    def get_tags(self, obj):
        return list(obj.tags.values_list("name", flat=True))

    def get_media(self, obj):
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(obj)
        qs = TrainingMedia.objects.filter(content_type=ct, object_id=obj.pk)
        request = self.context.get("request")
        return [
            {
                "original_filename": m.original_filename,
                "url": request.build_absolute_uri(m.file.url) if (request and m.file) else m.url,
            }
            for m in qs
        ]
