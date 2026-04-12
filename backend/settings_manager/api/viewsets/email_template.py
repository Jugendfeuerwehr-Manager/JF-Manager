"""
Email Template ViewSet
"""

import logging
from typing import Any

from django.template import Context, Template
from django.utils.html import strip_tags
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from orders.models import EmailTemplate

from ..permissions import CanChangeSettings
from ..serializers.email_template import (
    EmailTemplateCreateUpdateSerializer,
    EmailTemplateDetailSerializer,
    EmailTemplateListSerializer,
    EmailTemplatePreviewResponseSerializer,
    EmailTemplatePreviewSerializer,
)

logger = logging.getLogger(__name__)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email templates

    Provides endpoints to:
    - List all email templates
    - Get template details
    - Create/Update/Delete templates
    - Preview templates with sample data
    - Get available variables for template types
    """
    permission_classes = [IsAuthenticated, CanChangeSettings]
    queryset = EmailTemplate.objects.all().order_by('template_type')

    def get_permissions(self):
        """
        Allow default_content action for any authenticated user
        since it's just reading template files, not modifying settings
        """
        if self.action == 'default_content':
            return [IsAuthenticated()]
        return super().get_permissions()

    # Variable definitions for each template type
    TEMPLATE_VARIABLES = {
        'order_created': {
            'variables': [
                {'name': 'order', 'type': 'Order', 'description': 'Bestellungsobjekt',
                 'properties': ['pk', 'ordered_at', 'notes', 'total_amount']},
                {'name': 'member', 'type': 'Member', 'description': 'Mitglied',
                 'properties': ['first_name', 'last_name', 'email', 'phone']},
                {'name': 'order_url', 'type': 'string', 'description': 'URL zur Bestellung'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain der Anwendung'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll (http/https)'},
                {'name': 'timestamp', 'type': 'datetime', 'description': 'Zeitstempel der Benachrichtigung'},
            ],
            'sample_data': {
                'order': {'pk': 42, 'ordered_at': '2025-11-23', 'notes': 'Dringend', 'total_amount': '150.00'},
                'member': {'first_name': 'Max', 'last_name': 'Mustermann', 'email': 'max@example.com', 'phone': '0123456789'},
                'order_url': 'https://example.com/orders/42',
                'domain': 'example.com',
                'protocol': 'https',
                'timestamp': '2025-11-23 14:30:00',
            }
        },
        'status_update': {
            'variables': [
                {'name': 'order', 'type': 'Order', 'description': 'Bestellungsobjekt'},
                {'name': 'order_item', 'type': 'OrderItem', 'description': 'Bestellartikel',
                 'properties': ['quantity', 'size', 'notes']},
                {'name': 'item', 'type': 'OrderableItem', 'description': 'Artikel',
                 'properties': ['name', 'description', 'category']},
                {'name': 'member', 'type': 'Member', 'description': 'Mitglied'},
                {'name': 'old_status', 'type': 'OrderStatus', 'description': 'Alter Status',
                 'properties': ['name', 'color']},
                {'name': 'new_status', 'type': 'OrderStatus', 'description': 'Neuer Status',
                 'properties': ['name', 'color']},
                {'name': 'updated_by', 'type': 'User', 'description': 'Aktualisiert von',
                 'properties': ['first_name', 'last_name', 'email']},
                {'name': 'order_url', 'type': 'string', 'description': 'URL zur Bestellung'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
                {'name': 'timestamp', 'type': 'datetime', 'description': 'Zeitstempel'},
            ],
            'sample_data': {
                'order': {'pk': 42},
                'order_item': {'quantity': 2, 'size': 'M', 'notes': 'Mit Logo'},
                'item': {'name': 'T-Shirt', 'description': 'Blaues T-Shirt', 'category': 'Bekleidung'},
                'member': {'first_name': 'Max', 'last_name': 'Mustermann'},
                'old_status': {'name': 'Bestellt', 'color': 'blue'},
                'new_status': {'name': 'Geliefert', 'color': 'green'},
                'updated_by': {'first_name': 'Admin', 'last_name': 'User', 'email': 'admin@example.com'},
                'order_url': 'https://example.com/orders/42',
                'domain': 'example.com',
                'protocol': 'https',
                'timestamp': '2025-11-23 14:30:00',
            }
        },
        'bulk_update': {
            'variables': [
                {'name': 'order', 'type': 'Order', 'description': 'Bestellungsobjekt'},
                {'name': 'member', 'type': 'Member', 'description': 'Mitglied'},
                {'name': 'updated_items', 'type': 'list', 'description': 'Liste aktualisierter Artikel'},
                {'name': 'new_status', 'type': 'OrderStatus', 'description': 'Neuer Status'},
                {'name': 'updated_by', 'type': 'User', 'description': 'Aktualisiert von'},
                {'name': 'order_url', 'type': 'string', 'description': 'URL zur Bestellung'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
                {'name': 'timestamp', 'type': 'datetime', 'description': 'Zeitstempel'},
            ],
            'sample_data': {
                'order': {'pk': 42},
                'member': {'first_name': 'Max', 'last_name': 'Mustermann'},
                'updated_items': [
                    {'name': 'T-Shirt', 'quantity': 2},
                    {'name': 'Hose', 'quantity': 1}
                ],
                'new_status': {'name': 'Geliefert', 'color': 'green'},
                'updated_by': {'first_name': 'Admin', 'last_name': 'User'},
                'order_url': 'https://example.com/orders/42',
                'domain': 'example.com',
                'protocol': 'https',
                'timestamp': '2025-11-23 14:30:00',
            }
        },
        'pending_reminder': {
            'variables': [
                {'name': 'order', 'type': 'Order', 'description': 'Bestellungsobjekt'},
                {'name': 'member', 'type': 'Member', 'description': 'Mitglied'},
                {'name': 'pending_items', 'type': 'list', 'description': 'Liste offener Artikel'},
                {'name': 'days_pending', 'type': 'int', 'description': 'Tage seit Bestellung'},
                {'name': 'order_url', 'type': 'string', 'description': 'URL zur Bestellung'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
                {'name': 'timestamp', 'type': 'datetime', 'description': 'Zeitstempel'},
            ],
            'sample_data': {
                'order': {'pk': 42, 'ordered_at': '2025-11-10'},
                'member': {'first_name': 'Max', 'last_name': 'Mustermann'},
                'pending_items': [
                    {'name': 'T-Shirt', 'quantity': 2, 'status': 'Bestellt'},
                    {'name': 'Hose', 'quantity': 1, 'status': 'Bestellt'}
                ],
                'days_pending': 13,
                'order_url': 'https://example.com/orders/42',
                'domain': 'example.com',
                'protocol': 'https',
                'timestamp': '2025-11-23 14:30:00',
            }
        },
        'daily_summary': {
            'variables': [
                {'name': 'orders', 'type': 'QuerySet', 'description': 'Bestellungen des Tages'},
                {'name': 'order_count', 'type': 'int', 'description': 'Anzahl Bestellungen'},
                {'name': 'total_items', 'type': 'int', 'description': 'Anzahl Artikel gesamt'},
                {'name': 'date', 'type': 'date', 'description': 'Datum der Zusammenfassung'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
                {'name': 'timestamp', 'type': 'datetime', 'description': 'Zeitstempel'},
            ],
            'sample_data': {
                'orders': [
                    {'pk': 42, 'member': {'first_name': 'Max', 'last_name': 'Mustermann'}, 'total_amount': '150.00'},
                    {'pk': 43, 'member': {'first_name': 'Anna', 'last_name': 'Schmidt'}, 'total_amount': '75.00'}
                ],
                'order_count': 2,
                'total_items': 5,
                'date': '2025-11-23',
                'domain': 'example.com',
                'protocol': 'https',
                'timestamp': '2025-11-23 14:30:00',
            }
        },
        'weekly_report': {
            'variables': [
                {'name': 'orders', 'type': 'QuerySet', 'description': 'Bestellungen der Woche'},
                {'name': 'order_count', 'type': 'int', 'description': 'Anzahl Bestellungen'},
                {'name': 'total_items', 'type': 'int', 'description': 'Anzahl Artikel gesamt'},
                {'name': 'week_start', 'type': 'date', 'description': 'Wochenstart'},
                {'name': 'week_end', 'type': 'date', 'description': 'Wochenende'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
                {'name': 'timestamp', 'type': 'datetime', 'description': 'Zeitstempel'},
            ],
            'sample_data': {
                'orders': [
                    {'pk': 42, 'member': {'first_name': 'Max', 'last_name': 'Mustermann'}},
                    {'pk': 43, 'member': {'first_name': 'Anna', 'last_name': 'Schmidt'}}
                ],
                'order_count': 2,
                'total_items': 8,
                'week_start': '2025-11-17',
                'week_end': '2025-11-23',
                'domain': 'example.com',
                'protocol': 'https',
                'timestamp': '2025-11-23 14:30:00',
            }
        },
        # Legacy template types (for backward compatibility)
        'order_confirmed': {
            'variables': [
                {'name': 'order', 'type': 'Order', 'description': 'Bestellungsobjekt',
                 'properties': ['pk', 'ordered_at', 'notes']},
                {'name': 'member', 'type': 'Member', 'description': 'Mitglied',
                 'properties': ['first_name', 'last_name', 'email']},
                {'name': 'order_url', 'type': 'string', 'description': 'URL zur Bestellung'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
            ],
            'sample_data': {
                'order': {'pk': 42, 'ordered_at': '2025-11-23', 'notes': 'Bestätigt'},
                'member': {'first_name': 'Max', 'last_name': 'Mustermann', 'email': 'max@example.com'},
                'order_url': 'https://example.com/orders/42',
                'domain': 'example.com',
                'protocol': 'https',
            }
        },
        'order_shipped': {
            'variables': [
                {'name': 'order', 'type': 'Order', 'description': 'Bestellungsobjekt'},
                {'name': 'member', 'type': 'Member', 'description': 'Mitglied'},
                {'name': 'tracking_number', 'type': 'string', 'description': 'Tracking-Nummer'},
                {'name': 'order_url', 'type': 'string', 'description': 'URL zur Bestellung'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
            ],
            'sample_data': {
                'order': {'pk': 42},
                'member': {'first_name': 'Max', 'last_name': 'Mustermann'},
                'tracking_number': 'DHL1234567890',
                'order_url': 'https://example.com/orders/42',
                'domain': 'example.com',
                'protocol': 'https',
            }
        },
        'order_cancelled': {
            'variables': [
                {'name': 'order', 'type': 'Order', 'description': 'Bestellungsobjekt'},
                {'name': 'member', 'type': 'Member', 'description': 'Mitglied'},
                {'name': 'reason', 'type': 'string', 'description': 'Stornierungsgrund'},
                {'name': 'order_url', 'type': 'string', 'description': 'URL zur Bestellung'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
            ],
            'sample_data': {
                'order': {'pk': 42},
                'member': {'first_name': 'Max', 'last_name': 'Mustermann'},
                'reason': 'Auf Kundenwunsch',
                'order_url': 'https://example.com/orders/42',
                'domain': 'example.com',
                'protocol': 'https',
            }
        },
        'order_summary': {
            'variables': [
                {'name': 'orders', 'type': 'QuerySet', 'description': 'Bestellungen'},
                {'name': 'order_count', 'type': 'int', 'description': 'Anzahl Bestellungen'},
                {'name': 'total_items', 'type': 'int', 'description': 'Anzahl Artikel gesamt'},
                {'name': 'domain', 'type': 'string', 'description': 'Domain'},
                {'name': 'protocol', 'type': 'string', 'description': 'Protokoll'},
            ],
            'sample_data': {
                'orders': [
                    {'pk': 42, 'member': {'first_name': 'Max', 'last_name': 'Mustermann'}},
                    {'pk': 43, 'member': {'first_name': 'Anna', 'last_name': 'Schmidt'}}
                ],
                'order_count': 2,
                'total_items': 5,
                'domain': 'example.com',
                'protocol': 'https',
            }
        },
    }

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return EmailTemplateListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return EmailTemplateCreateUpdateSerializer
        elif self.action == 'preview':
            return EmailTemplatePreviewSerializer
        return EmailTemplateDetailSerializer

    @staticmethod
    def get_template_variables(template_type: str) -> dict[str, Any]:
        """Get available variables for a template type"""
        return EmailTemplateViewSet.TEMPLATE_VARIABLES.get(template_type, {
            'variables': [],
            'sample_data': {}
        })

    @extend_schema(
        summary="Get template variables",
        description="Get available template variables for all template types or a specific type",
        parameters=[
            OpenApiParameter(
                name='template_type',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by template type (optional)',
                required=False
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def variables(self, request):
        """
        GET /api/v1/settings/email-templates/variables/?template_type=order_created
        Returns available template variables for a specific template type.
        Returns empty variables list for unknown template types (legacy templates).
        """
        template_type = request.query_params.get('template_type')

        if template_type:
            # For unknown template types (e.g., legacy templates), return empty variables with warning
            if template_type not in self.TEMPLATE_VARIABLES:
                return Response({
                    'template_type': template_type,
                    'variables': [],
                    'sample_data': {},
                    'warning': f'No variable definitions for template type "{template_type}". This may be a legacy template.'
                })
            return Response({
                'template_type': template_type,
                **self.TEMPLATE_VARIABLES[template_type]
            })

        # Return all template variables
        return Response(self.TEMPLATE_VARIABLES)

    @extend_schema(
        summary="Preview template",
        description="Preview email template with sample data",
        request=EmailTemplatePreviewSerializer,
        responses={200: EmailTemplatePreviewResponseSerializer}
    )
    @action(detail=False, methods=['post'])
    def preview(self, request):
        """POST /api/v1/settings/email-templates/preview/"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        subject_template = data['subject_template']
        html_template = data['html_template']
        text_template = data.get('text_template', '')
        sample_data = data.get('sample_data', {})

        errors = []

        try:
            # Render subject
            subject = Template(subject_template).render(Context(sample_data))
        except Exception as e:
            errors.append(f'Subject template error: {e!s}')
            subject = ''

        try:
            # Render HTML
            html_content = Template(html_template).render(Context(sample_data))
        except Exception as e:
            errors.append(f'HTML template error: {e!s}')
            html_content = ''

        try:
            # Render text or strip HTML
            if text_template:
                text_content = Template(text_template).render(Context(sample_data))
            else:
                text_content = strip_tags(html_content) if html_content else ''
        except Exception as e:
            errors.append(f'Text template error: {e!s}')
            text_content = ''

        response_data = {
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content,
        }

        if errors:
            response_data['errors'] = errors

        return Response(response_data)

    @extend_schema(
        summary="Get template types",
        description="Get list of available template types"
    )
    @action(detail=False, methods=['get'])
    def types(self, request):
        """GET /api/v1/settings/email-templates/types/"""
        return Response([
            {'value': choice[0], 'label': choice[1]}
            for choice in EmailTemplate.TEMPLATE_TYPES
        ])

    @extend_schema(
        summary="Get default template content",
        description="Get default template content from files for a specific template type",
        parameters=[
            OpenApiParameter(
                name='template_type',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Template type to get default content for',
                required=True
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def default_content(self, request):
        """
        GET /api/v1/settings/email-templates/default-content/?template_type=order_created
        Returns the default template content from template files.
        """
        from django.template import TemplateDoesNotExist
        from django.template.loader import get_template

        template_type = request.query_params.get('template_type')
        if not template_type:
            return Response(
                {'error': 'template_type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Map template types to template file paths
        template_files = {
            'order_created': 'orders/emails/order_created.html',
            'order_confirmed': 'orders/emails/order_confirmed.html',
            'order_shipped': 'orders/emails/order_shipped.html',
            'order_cancelled': 'orders/emails/order_cancelled.html',
            'order_summary': 'orders/emails/order_summary.html',
            'status_update': 'orders/emails/status_update.html',
            'bulk_update': 'orders/emails/bulk_status_update.html',
            'pending_reminder': 'orders/emails/pending_reminder.html',
        }

        if template_type not in template_files:
            return Response(
                {'error': f'No default template file for type: {template_type}'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            template_path = template_files[template_type]
            django_template = get_template(template_path)
            html_content = django_template.template.source

            # Get default subject from TEMPLATE_VARIABLES or construct one
            type_label = dict(EmailTemplate.TEMPLATE_TYPES).get(template_type, template_type)
            subject = f'{type_label} - JF-Manager'

            return Response({
                'template_type': template_type,
                'subject_template': subject,
                'html_template': html_content,
                'text_template': '',
            })

        except TemplateDoesNotExist:
            return Response(
                {'error': f'Template file not found: {template_files[template_type]}'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f'Failed to load default template: {e}')
            return Response(
                {'error': f'Failed to load template: {e!s}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_destroy(self, instance):
        """Clear template cache when template is deleted"""
        from orders.notifications.template_service import TemplateRenderer
        TemplateRenderer.clear_template_cache(instance.template_type)
        super().perform_destroy(instance)

    def perform_update(self, serializer):
        """Clear template cache when template is updated"""
        from orders.notifications.template_service import TemplateRenderer
        instance = serializer.save()
        TemplateRenderer.clear_template_cache(instance.template_type)
        return instance
