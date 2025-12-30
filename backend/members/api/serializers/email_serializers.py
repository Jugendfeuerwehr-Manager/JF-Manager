"""
API serializers for email messaging system.
"""

from rest_framework import serializers
from members.models import EmailMessage, EmailRecipient, Group, Member


class EmailRecipientSerializer(serializers.ModelSerializer):
    """Serializer for EmailRecipient model."""
    
    class Meta:
        model = EmailRecipient
        fields = [
            'id',
            'email_address',
            'recipient_name',
            'member',
            'status',
            'sent_at',
            'error_message',
        ]
        read_only_fields = ['id', 'sent_at']


class EmailMessageListSerializer(serializers.ModelSerializer):
    """Serializer for listing email messages."""
    
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    recipient_group_name = serializers.CharField(source='recipient_group.name', read_only=True, allow_null=True)
    recipient_member_name = serializers.CharField(source='recipient_member.get_full_name', read_only=True, allow_null=True)
    recipient_type_display = serializers.CharField(source='get_recipient_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = EmailMessage
        fields = [
            'id',
            'sender',
            'sender_name',
            'subject',
            'recipient_type',
            'recipient_type_display',
            'recipient_group',
            'recipient_group_name',
            'recipient_member',
            'recipient_member_name',
            'status',
            'status_display',
            'total_recipients',
            'successful_sends',
            'failed_sends',
            'created_at',
            'sent_at',
        ]
        read_only_fields = [
            'id',
            'sender',
            'sender_name',
            'status',
            'total_recipients',
            'successful_sends',
            'failed_sends',
            'created_at',
            'sent_at',
        ]


class EmailMessageDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed email message view."""
    
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    recipient_group_name = serializers.CharField(source='recipient_group.name', read_only=True, allow_null=True)
    recipient_member_name = serializers.CharField(source='recipient_member.get_full_name', read_only=True, allow_null=True)
    recipient_type_display = serializers.CharField(source='get_recipient_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recipients = EmailRecipientSerializer(many=True, read_only=True)
    
    class Meta:
        model = EmailMessage
        fields = [
            'id',
            'sender',
            'sender_name',
            'subject',
            'body_html',
            'body_text',
            'recipient_type',
            'recipient_type_display',
            'recipient_group',
            'recipient_group_name',
            'recipient_member',
            'recipient_member_name',
            'status',
            'status_display',
            'total_recipients',
            'successful_sends',
            'failed_sends',
            'error_message',
            'created_at',
            'sent_at',
            'recipients',
        ]
        read_only_fields = [
            'id',
            'sender',
            'sender_name',
            'status',
            'total_recipients',
            'successful_sends',
            'failed_sends',
            'error_message',
            'created_at',
            'sent_at',
            'recipients',
        ]


class EmailMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating email messages."""
    
    class Meta:
        model = EmailMessage
        fields = [
            'subject',
            'body_html',
            'body_text',
            'recipient_type',
            'recipient_group',
            'recipient_member',
        ]
    
    def validate(self, data):
        """Validate recipient selection."""
        recipient_type = data.get('recipient_type')
        
        if recipient_type == 'group' and not data.get('recipient_group'):
            raise serializers.ValidationError({
                'recipient_group': 'Gruppe muss ausgewählt werden, wenn Empfängertyp "Gruppe" ist.'
            })
        
        if recipient_type == 'individual' and not data.get('recipient_member'):
            raise serializers.ValidationError({
                'recipient_member': 'Mitglied muss ausgewählt werden, wenn Empfängertyp "Einzelnes Mitglied" ist.'
            })
        
        return data
    
    def create(self, validated_data):
        """Set sender from request user."""
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class EmailTemplateVariablesSerializer(serializers.Serializer):
    """Serializer for available template variables."""
    
    variable = serializers.CharField()
    description = serializers.CharField()


class EmailPreviewRequestSerializer(serializers.Serializer):
    """Serializer for email preview requests."""
    
    subject = serializers.CharField(required=False, allow_blank=True)
    body_html = serializers.CharField()
    body_text = serializers.CharField(required=False, allow_blank=True)
    member_id = serializers.IntegerField()
    
    def validate_member_id(self, value):
        """Validate that member exists."""
        if not Member.objects.filter(id=value).exists():
            raise serializers.ValidationError('Mitglied nicht gefunden.')
        return value


class EmailPreviewResponseSerializer(serializers.Serializer):
    """Serializer for email preview response."""
    
    rendered_html = serializers.CharField()
    rendered_text = serializers.CharField()
    member_name = serializers.CharField()
    recipient_count = serializers.IntegerField()
