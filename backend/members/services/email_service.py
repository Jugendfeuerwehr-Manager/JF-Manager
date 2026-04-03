"""
Email sending service for member communications.
Handles recipient collection, personalization, and SMTP delivery.
"""

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.template import Template, Context
from django.utils.html import strip_tags
from typing import List, Dict, Set, Optional
import logging
import re

from members.models import Member, Parent, Group, EmailMessage, EmailRecipient

logger = logging.getLogger(__name__)


class EmailRecipientCollector:
    """
    Collects email addresses for members based on recipient type.
    Handles parent emails and deduplication logic.
    """
    
    @staticmethod
    def get_member_emails(member: Member) -> List[Dict[str, str]]:
        """
        Get all email addresses for a member (parents + own email if exists).
        
        Returns list of dicts with:
        - email: The email address
        - name: Recipient name
        - member_id: Associated member ID
        """
        emails = []
        seen_emails: Set[str] = set()
        
        # Get parent emails
        parents = Parent.objects.filter(children=member).distinct()
        for parent in parents:
            # Add primary email
            if parent.email and parent.email.strip():
                email_lower = parent.email.lower().strip()
                if email_lower not in seen_emails:
                    emails.append({
                        'email': parent.email.strip(),
                        'name': parent.get_full_name(),
                        'member_id': member.id,
                        'member_name': member.get_full_name()
                    })
                    seen_emails.add(email_lower)
            
            # Add secondary email
            if parent.email2 and parent.email2.strip():
                email_lower = parent.email2.lower().strip()
                if email_lower not in seen_emails:
                    emails.append({
                        'email': parent.email2.strip(),
                        'name': parent.get_full_name(),
                        'member_id': member.id,
                        'member_name': member.get_full_name()
                    })
                    seen_emails.add(email_lower)
        
        # Add member's own email if exists and not duplicate
        if member.email and member.email.strip():
            email_lower = member.email.lower().strip()
            if email_lower not in seen_emails:
                emails.append({
                    'email': member.email.strip(),
                    'name': member.get_full_name(),
                    'member_id': member.id,
                    'member_name': member.get_full_name()
                })
                seen_emails.add(email_lower)
        
        return emails
    
    @classmethod
    def get_recipients_for_all_members(cls) -> List[Dict[str, str]]:
        """Get all recipients for all active members."""
        recipients = []
        members = Member.objects.all()
        
        for member in members:
            recipients.extend(cls.get_member_emails(member))
        
        return recipients
    
    @classmethod
    def get_recipients_for_group(cls, group: Group) -> List[Dict[str, str]]:
        """Get all recipients for members in a specific group."""
        recipients = []
        members = Member.objects.filter(group=group)
        
        for member in members:
            recipients.extend(cls.get_member_emails(member))
        
        return recipients
    
    @classmethod
    def get_recipients_for_member(cls, member: Member) -> List[Dict[str, str]]:
        """Get all recipients for a single member."""
        return cls.get_member_emails(member)


class EmailTemplateRenderer:
    """
    Handles template variable rendering for personalized emails.
    Supports variables like {{vorname}}, {{nachname}}, etc.
    """
    
    @staticmethod
    def get_available_variables() -> List[Dict[str, str]]:
        """
        Returns list of available template variables.
        Each dict contains 'variable' and 'description'.
        """
        return [
            {'variable': '{{vorname}}', 'description': 'Vorname des Mitglieds'},
            {'variable': '{{nachname}}', 'description': 'Nachname des Mitglieds'},
            {'variable': '{{vollername}}', 'description': 'Vollständiger Name des Mitglieds'},
        ]
    
    @staticmethod
    def render_for_member(template_html: str, template_text: str, member: Member, signature: str = '') -> tuple:
        """
        Render template with member-specific data.
        
        Args:
            template_html: HTML template string
            template_text: Plain text template string
            member: Member instance
            signature: User's email signature
            
        Returns:
            Tuple of (rendered_html, rendered_text)
        """
        context_data = {
            'vorname': member.name,
            'nachname': member.lastname,
            'vollername': member.get_full_name(),
        }
        
        # Simple string replacement for variables
        rendered_html = template_html
        rendered_text = template_text
        
        for key, value in context_data.items():
            rendered_html = rendered_html.replace(f'{{{{{key}}}}}', value or '')
            rendered_text = rendered_text.replace(f'{{{{{key}}}}}', value or '')
        
        # Add signature if provided
        if signature:
            rendered_html += f'<br><br>{signature}'
            # Strip HTML from signature for text version
            text_signature = strip_tags(signature)
            rendered_text += f'\n\n{text_signature}'
        
        return rendered_html, rendered_text


class MemberEmailService:
    """
    Main service for sending emails to members and their parents.
    """
    
    @staticmethod
    @transaction.atomic
    def create_email_message(
        sender,
        subject: str,
        body_html: str,
        body_text: str,
        recipient_type: str,
        recipient_group: Optional[Group] = None,
        recipient_member: Optional[Member] = None,
    ) -> EmailMessage:
        """
        Create a new email message record.
        
        Args:
            sender: User sending the email
            subject: Email subject
            body_html: HTML body
            body_text: Plain text body
            recipient_type: 'all', 'group', or 'individual'
            recipient_group: Group instance if recipient_type is 'group'
            recipient_member: Member instance if recipient_type is 'individual'
            
        Returns:
            EmailMessage instance
        """
        email_message = EmailMessage.objects.create(
            sender=sender,
            subject=subject,
            body_html=body_html,
            body_text=body_text or strip_tags(body_html),
            recipient_type=recipient_type,
            recipient_group=recipient_group,
            recipient_member=recipient_member,
            status='draft'
        )
        
        return email_message
    
    @staticmethod
    @transaction.atomic
    def prepare_recipients(email_message: EmailMessage) -> int:
        """
        Prepare recipient list for an email message.
        Creates EmailRecipient records for each recipient.
        
        Returns:
            Number of recipients prepared
        """
        # Collect recipients based on type
        if email_message.recipient_type == 'all':
            recipients = EmailRecipientCollector.get_recipients_for_all_members()
        elif email_message.recipient_type == 'group':
            recipients = EmailRecipientCollector.get_recipients_for_group(email_message.recipient_group)
        elif email_message.recipient_type == 'individual':
            recipients = EmailRecipientCollector.get_recipients_for_member(email_message.recipient_member)
        else:
            raise ValueError(f"Invalid recipient type: {email_message.recipient_type}")
        
        # Deduplicate by email address
        unique_recipients = {}
        for recipient in recipients:
            email = recipient['email'].lower()
            if email not in unique_recipients:
                unique_recipients[email] = recipient
        
        # Create EmailRecipient records
        # Note: Signature is already included in body_html by the frontend
        for email, recipient_data in unique_recipients.items():
            member = Member.objects.filter(id=recipient_data['member_id']).first()
            
            # Personalize content for this member
            personalized_html, personalized_text = EmailTemplateRenderer.render_for_member(
                email_message.body_html,
                email_message.body_text,
                member
            )
            
            EmailRecipient.objects.create(
                email_message=email_message,
                member=member,
                email_address=recipient_data['email'],
                recipient_name=recipient_data['name'],
                personalized_body_html=personalized_html,
                personalized_body_text=personalized_text,
                status='pending'
            )
        
        # Update email message with recipient count
        total_recipients = len(unique_recipients)
        email_message.total_recipients = total_recipients
        email_message.save(update_fields=['total_recipients'])
        
        return total_recipients
    
    @staticmethod
    @transaction.atomic
    def send_email_message(email_message: EmailMessage) -> Dict[str, int]:
        """
        Send an email message to all its recipients.
        
        Returns:
            Dict with 'successful' and 'failed' counts
        """
        email_message.status = 'sending'
        email_message.save(update_fields=['status'])
        
        successful = 0
        failed = 0
        
        # Pre-load attachments
        attachments = list(email_message.attachments.all())
        
        pending_recipients = email_message.recipients.filter(status='pending')
        
        for recipient in pending_recipients:
            try:
                # Create email
                email = EmailMultiAlternatives(
                    subject=email_message.subject,
                    body=recipient.personalized_body_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient.email_address],
                )
                
                # Attach HTML version
                email.attach_alternative(recipient.personalized_body_html, "text/html")
                
                # Attach files
                for attachment in attachments:
                    try:
                        attachment.file.seek(0)
                        email.attach(
                            attachment.original_filename,
                            attachment.file.read(),
                            attachment.content_type or 'application/octet-stream',
                        )
                    except Exception as attach_err:
                        logger.warning(f"Could not attach file {attachment.original_filename}: {attach_err}")
                
                # Send
                email.send(fail_silently=False)
                
                # Mark as sent
                recipient.status = 'sent'
                recipient.sent_at = timezone.now()
                recipient.save(update_fields=['status', 'sent_at'])
                
                successful += 1
                
            except Exception as e:
                logger.error(f"Failed to send email to {recipient.email_address}: {str(e)}")
                
                recipient.status = 'failed'
                recipient.error_message = str(e)[:1000]  # Limit error message length
                recipient.save(update_fields=['status', 'error_message'])
                
                failed += 1
        
        # Update email message status
        email_message.successful_sends = successful
        email_message.failed_sends = failed
        email_message.sent_at = timezone.now()
        
        if failed == 0:
            email_message.status = 'sent'
        elif successful == 0:
            email_message.status = 'failed'
            email_message.error_message = 'Alle E-Mails konnten nicht zugestellt werden'
        else:
            email_message.status = 'partial'
            email_message.error_message = f'{failed} von {successful + failed} E-Mails konnten nicht zugestellt werden'
        
        email_message.save()
        
        return {
            'successful': successful,
            'failed': failed
        }
