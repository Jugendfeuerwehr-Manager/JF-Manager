"""
API viewsets for email messaging system.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils.html import strip_tags
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from members.models import EmailMessage, EmailRecipient, EmailAttachment, Member
from members.services.email_service import (
    MemberEmailService,
    EmailTemplateRenderer,
    EmailRecipientCollector
)
from members.api.serializers.email_serializers import (
    EmailMessageListSerializer,
    EmailMessageDetailSerializer,
    EmailMessageCreateSerializer,
    EmailTemplateVariablesSerializer,
    EmailPreviewRequestSerializer,
    EmailPreviewResponseSerializer,
    EmailRecipientSerializer,
)
from members.api.permissions import CanSendEmails


class EmailMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email messages.
    
    Provides endpoints for creating, listing, and sending emails to members.
    """
    
    queryset = EmailMessage.objects.all()
    permission_classes = [IsAuthenticated, CanSendEmails]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['subject', 'recipient_member__name', 'recipient_member__lastname']
    filterset_fields = ['status', 'recipient_type', 'recipient_group', 'sender']
    ordering_fields = ['created_at', 'sent_at', 'subject']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return EmailMessageListSerializer
        elif self.action == 'create':
            return EmailMessageCreateSerializer
        return EmailMessageDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        
        # Non-staff users can only see their own emails
        if not self.request.user.is_staff:
            queryset = queryset.filter(sender=self.request.user)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def send(self, request):
        """
        Create and send an email message with optional file attachments.
        
        POST /api/v1/emails/send/
        
        Accepts multipart/form-data with:
        - subject, body_html, body_text, recipient_type, recipient_group, recipient_member
        - attachments: one or more files (field name: "attachments")
        """
        create_serializer = EmailMessageCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        create_serializer.is_valid(raise_exception=True)
        
        # Create email message
        email_message = create_serializer.save()
        
        # Handle file attachments
        ALLOWED_CONTENT_TYPES = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain', 'text/csv',
        }
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

        files = request.FILES.getlist('attachments')
        for f in files:
            if f.content_type not in ALLOWED_CONTENT_TYPES:
                email_message.delete()
                return Response(
                    {'error': f'Dateityp "{f.content_type}" ist nicht erlaubt für "{f.name}".'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if f.size > MAX_FILE_SIZE:
                email_message.delete()
                return Response(
                    {'error': f'Datei "{f.name}" ist zu groß (max. 10 MB).'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            EmailAttachment.objects.create(
                email_message=email_message,
                file=f,
                original_filename=f.name,
                file_size=f.size,
                content_type=f.content_type or '',
            )
        
        try:
            # Prepare recipients
            recipient_count = MemberEmailService.prepare_recipients(email_message)
            
            if recipient_count == 0:
                return Response(
                    {'error': 'Keine Empfänger gefunden'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Send emails
            result = MemberEmailService.send_email_message(email_message)
            
            # Return detailed response
            detail_serializer = EmailMessageDetailSerializer(email_message)
            
            return Response({
                'email': detail_serializer.data,
                'result': result
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            email_message.status = 'failed'
            email_message.error_message = str(e)
            email_message.save()
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """
        Resend failed recipients for an email message.
        
        POST /api/v1/emails/{id}/resend/
        """
        email_message = self.get_object()
        
        # Reset failed recipients to pending
        failed_recipients = email_message.recipients.filter(status='failed')
        failed_recipients.update(status='pending', error_message='')
        
        # Send again
        result = MemberEmailService.send_email_message(email_message)
        
        detail_serializer = EmailMessageDetailSerializer(email_message)
        
        return Response({
            'email': detail_serializer.data,
            'result': result
        })
    
    @action(detail=False, methods=['post'])
    def preview(self, request):
        """
        Preview an email with template rendering for a specific member.
        
        POST /api/v1/emails/preview/
        
        Request body:
        {
            "subject": "Email subject",
            "body_html": "<p>Hello {{vorname}}</p>",
            "body_text": "Hello {{vorname}}",
            "member_id": 1
        }
        """
        request_serializer = EmailPreviewRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        
        member = Member.objects.get(id=request_serializer.validated_data['member_id'])
        
        # Render template (signature is already included in body_html by the frontend)
        rendered_html, rendered_text = EmailTemplateRenderer.render_for_member(
            request_serializer.validated_data['body_html'],
            request_serializer.validated_data.get('body_text', ''),
            member
        )
        
        # Get recipient count for this member
        recipients = EmailRecipientCollector.get_member_emails(member)
        
        response_data = {
            'rendered_html': rendered_html,
            'rendered_text': rendered_text,
            'member_name': member.get_full_name(),
            'recipient_count': len(recipients)
        }
        
        response_serializer = EmailPreviewResponseSerializer(response_data)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['get'])
    def template_variables(self, request):
        """
        Get list of available template variables.
        
        GET /api/v1/emails/template_variables/
        """
        variables = EmailTemplateRenderer.get_available_variables()
        serializer = EmailTemplateVariablesSerializer(variables, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def recipient_count(self, request):
        """
        Get count of recipients for given selection criteria.
        
        POST /api/v1/emails/recipient_count/
        
        Request body:
        {
            "recipient_type": "all|group|individual",
            "recipient_group": 1,  // if type is "group"
            "recipient_member": 1   // if type is "individual"
        }
        """
        recipient_type = request.data.get('recipient_type')
        
        if recipient_type == 'all':
            recipients = EmailRecipientCollector.get_recipients_for_all_members()
        elif recipient_type == 'group':
            from members.models import Group
            group_id = request.data.get('recipient_group')
            if not group_id:
                return Response(
                    {'error': 'recipient_group erforderlich'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            group = Group.objects.get(id=group_id)
            recipients = EmailRecipientCollector.get_recipients_for_group(group)
        elif recipient_type == 'individual':
            member_id = request.data.get('recipient_member')
            if not member_id:
                return Response(
                    {'error': 'recipient_member erforderlich'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            member = Member.objects.get(id=member_id)
            recipients = EmailRecipientCollector.get_recipients_for_member(member)
        else:
            return Response(
                {'error': 'Ungültiger recipient_type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Deduplicate
        unique_emails = set(r['email'].lower() for r in recipients)
        
        return Response({
            'count': len(unique_emails),
            'recipients': recipients
        })
