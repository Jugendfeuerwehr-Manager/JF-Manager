"""
Template rendering service for email notifications.

This module handles email template management, rendering, and caching.
"""

from django.template import Template, Context
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.cache import cache
from typing import Dict, Any, Optional, Tuple
import logging

from ..models import EmailTemplate
from .base import BaseNotificationService, TemplateNotFoundError

logger = logging.getLogger(__name__)


class TemplateRenderer(BaseNotificationService):
    """
    Service for rendering email templates with caching and fallback support.
    
    Handles both custom email templates from the database and default
    template files, with intelligent caching for performance.
    """
    
    CACHE_TIMEOUT = 3600  # 1 hour
    DEFAULT_TEMPLATES = {
        'order_created': {
            'subject': 'Neue Bestellung #{order.pk} für {member_name}',
            'template': 'orders/emails/order_created.html'
        },
        'status_update': {
            'subject': 'Status-Update: {item_name} für {member_name}',
            'template': 'orders/emails/status_update.html'
        },
        'bulk_update': {
            'subject': 'Bulk Status-Update für Bestellung #{order.pk}',
            'template': 'orders/emails/bulk_status_update.html'
        },
        'pending_reminder': {
            'subject': 'Erinnerung: Offene Bestellartikel in Bestellung #{order.pk}',
            'template': 'orders/emails/pending_reminder.html'
        },
        'order_summary': {
            'subject': 'Bestellübersicht JF-Manager - {order_count} Bestellungen ({total_items} Artikel)',
            'template': 'orders/emails/order_summary.html'
        }
    }
    
    @classmethod
    def get_email_template(cls, template_type: str) -> Optional[EmailTemplate]:
        """
        Get custom email template from database with caching.
        
        Args:
            template_type: Type of email template to retrieve
            
        Returns:
            EmailTemplate instance or None if not found
        """
        cache_key = f"email_template_{template_type}"
        template = cache.get(cache_key)
        
        if template is None:
            try:
                template = EmailTemplate.objects.get(
                    template_type=template_type, 
                    is_active=True
                )
                cache.set(cache_key, template, cls.CACHE_TIMEOUT)
            except EmailTemplate.DoesNotExist:
                # Cache the fact that no template exists
                cache.set(cache_key, False, cls.CACHE_TIMEOUT)
                template = False
        
        return template if template else None
    
    @classmethod
    def render_template_string(cls, template_content: str, context: Dict[str, Any]) -> str:
        """
        Render a Django template string with the given context.
        
        Args:
            template_content: Template string to render
            context: Context variables for template rendering
            
        Returns:
            Rendered template as string
            
        Raises:
            TemplateNotFoundError: If template rendering fails
        """
        try:
            template = Template(template_content)
            return template.render(Context(context))
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            raise TemplateNotFoundError(f"Failed to render template: {e}")
    
    @classmethod
    def render_email_content(
        cls, 
        template_type: str, 
        context: Dict[str, Any]
    ) -> Tuple[str, str, str]:
        """
        Render complete email content (subject, HTML, plain text).
        
        Args:
            template_type: Type of email template
            context: Context variables for rendering
            
        Returns:
            Tuple of (subject, html_message, plain_message)
            
        Raises:
            TemplateNotFoundError: If no suitable template is found
        """
        # Try to get custom template first
        email_template = cls.get_email_template(template_type)
        
        if email_template:
            return cls._render_custom_template(email_template, context)
        else:
            return cls._render_default_template(template_type, context)
    
    @classmethod
    def _render_custom_template(
        cls, 
        email_template: EmailTemplate, 
        context: Dict[str, Any]
    ) -> Tuple[str, str, str]:
        """
        Render custom email template from database.
        
        Args:
            email_template: EmailTemplate instance
            context: Context variables
            
        Returns:
            Tuple of (subject, html_message, plain_message)
        """
        try:
            subject = cls.render_template_string(email_template.subject_template, context)
            html_message = cls.render_template_string(email_template.html_template, context)
            
            # Use custom text template if available, otherwise strip HTML
            if email_template.text_template:
                plain_message = cls.render_template_string(email_template.text_template, context)
            else:
                plain_message = strip_tags(html_message)
            
            return subject, html_message, plain_message
            
        except Exception as e:
            logger.error(f"Custom template rendering failed: {e}")
            raise TemplateNotFoundError(f"Failed to render custom template: {e}")
    
    @classmethod
    def _render_default_template(
        cls, 
        template_type: str, 
        context: Dict[str, Any]
    ) -> Tuple[str, str, str]:
        """
        Render default email template from files.
        
        Args:
            template_type: Type of email template
            context: Context variables
            
        Returns:
            Tuple of (subject, html_message, plain_message)
            
        Raises:
            TemplateNotFoundError: If default template is not configured
        """
        if template_type not in cls.DEFAULT_TEMPLATES:
            raise TemplateNotFoundError(f"No default template configured for {template_type}")
        
        default_config = cls.DEFAULT_TEMPLATES[template_type]
        
        try:
            # Render subject with context substitution
            subject_template = default_config['subject']
            subject = cls._render_subject_template(subject_template, context)
            
            # Render HTML template
            html_message = render_to_string(default_config['template'], context)
            plain_message = strip_tags(html_message)
            
            return subject, html_message, plain_message
            
        except Exception as e:
            logger.error(f"Default template rendering failed: {e}")
            raise TemplateNotFoundError(f"Failed to render default template: {e}")
    
    @classmethod
    def _render_subject_template(cls, subject_template: str, context: Dict[str, Any]) -> str:
        """
        Render subject template with simple variable substitution.
        
        Args:
            subject_template: Subject template string
            context: Context variables
            
        Returns:
            Rendered subject string
        """
        # Extract commonly used variables for subject templates
        replacements = {}
        
        if 'order' in context:
            replacements['order.pk'] = str(context['order'].pk)
        
        if 'member' in context:
            member = context['member']
            replacements['member_name'] = member.get_full_name() if hasattr(member, 'get_full_name') else str(member)
        
        if 'order_item' in context:
            item = context['order_item']
            replacements['item_name'] = item.item.name if hasattr(item, 'item') else str(item)
        
        if 'orders' in context:
            replacements['order_count'] = str(context['orders'].count() if hasattr(context['orders'], 'count') else len(context['orders']))
        
        if 'total_items' in context:
            replacements['total_items'] = str(context['total_items'])
        
        # Simple template variable replacement
        result = subject_template
        for key, value in replacements.items():
            result = result.replace(f'{{{key}}}', value)
        
        return result
    
    @classmethod
    def clear_template_cache(cls, template_type: str = None):
        """
        Clear template cache for specific type or all templates.
        
        Args:
            template_type: Specific template type to clear, or None for all
        """
        if template_type:
            cache_key = f"email_template_{template_type}"
            cache.delete(cache_key)
        else:
            # Clear all email template caches
            for tmpl_type in cls.DEFAULT_TEMPLATES.keys():
                cache_key = f"email_template_{tmpl_type}"
                cache.delete(cache_key)
