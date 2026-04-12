"""
Email Template Serializers
"""

from rest_framework import serializers

from orders.models import EmailTemplate


class EmailTemplateListSerializer(serializers.ModelSerializer):
    """Serializer for listing email templates"""
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)

    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'template_type', 'template_type_display',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class EmailTemplateDetailSerializer(serializers.ModelSerializer):
    """Serializer for email template details"""
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    available_variables = serializers.SerializerMethodField()

    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'template_type', 'template_type_display',
            'subject_template', 'html_template', 'text_template',
            'is_active', 'available_variables',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'available_variables']

    def get_available_variables(self, obj):
        """Get available template variables for this template type"""
        from ..viewsets.email_template import EmailTemplateViewSet
        return EmailTemplateViewSet.get_template_variables(obj.template_type)


class EmailTemplateCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating email templates"""

    class Meta:
        model = EmailTemplate
        fields = [
            'name', 'template_type', 'subject_template',
            'html_template', 'text_template', 'is_active'
        ]

    def validate_template_type(self, value):
        """Ensure template type is unique when creating"""
        if self.instance is None:  # Creating new template
            if EmailTemplate.objects.filter(template_type=value).exists():
                raise serializers.ValidationError(
                    f'Eine Vorlage für "{value}" existiert bereits.'
                )
        elif self.instance.template_type != value and EmailTemplate.objects.filter(template_type=value).exists():
            raise serializers.ValidationError(
                f'Eine Vorlage für "{value}" existiert bereits.'
            )
        return value

    def validate_html_template(self, value):
        """Validate HTML template syntax"""
        from django.template import Template, TemplateSyntaxError
        try:
            Template(value)
        except TemplateSyntaxError as e:
            raise serializers.ValidationError(f'Template-Syntaxfehler: {e!s}') from e
        return value

    def validate_subject_template(self, value):
        """Validate subject template syntax"""
        from django.template import Template, TemplateSyntaxError
        try:
            Template(value)
        except TemplateSyntaxError as e:
            raise serializers.ValidationError(f'Template-Syntaxfehler: {e!s}') from e
        return value


class EmailTemplatePreviewSerializer(serializers.Serializer):
    """Serializer for template preview"""
    subject_template = serializers.CharField(required=True)
    html_template = serializers.CharField(required=True)
    text_template = serializers.CharField(required=False, allow_blank=True)
    sample_data = serializers.JSONField(required=False, default=dict)


class EmailTemplatePreviewResponseSerializer(serializers.Serializer):
    """Response serializer for template preview"""
    subject = serializers.CharField()
    html_content = serializers.CharField()
    text_content = serializers.CharField()
    errors = serializers.ListField(child=serializers.CharField(), required=False)
