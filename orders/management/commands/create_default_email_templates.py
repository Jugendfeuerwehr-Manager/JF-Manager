from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from orders.models import EmailTemplate
import os


class Command(BaseCommand):
    help = 'Create default email templates for notifications'

    def load_template_content(self, template_name, template_type='html'):
        """Load template content from file"""
        template_path = f'orders/emails/{template_name}.{template_type}'
        try:
            template = get_template(template_path)
            return template.template.source
        except TemplateDoesNotExist:
            self.stdout.write(
                self.style.WARNING(f'Template file not found: {template_path}')
            )
            return ''

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Bestellung erstellt',
                'template_type': 'order_created',
                'subject_template': 'Ihre Bestellung wurde erstellt - Bestellung #{{ order.id }}',
                'text_template': self.load_template_content('order_created', 'txt'),
                'html_template': self.load_template_content('order_created', 'html'),
                'is_active': True
            },
            {
                'name': 'Bestellung bestätigt',
                'template_type': 'order_confirmed',
                'subject_template': 'Ihre Bestellung wurde bestätigt - Bestellung #{{ order.id }}',
                'text_template': self.load_template_content('order_confirmed', 'txt'),
                'html_template': self.load_template_content('order_confirmed', 'html'),
                'is_active': True
            },
            {
                'name': 'Bestellung versandt',
                'template_type': 'order_shipped',
                'subject_template': 'Ihre Bestellung wurde versandt - Bestellung #{{ order.id }}',
                'text_template': self.load_template_content('order_shipped', 'txt'),
                'html_template': self.load_template_content('order_shipped', 'html'),
                'is_active': True
            },
            {
                'name': 'Bestellung storniert',
                'template_type': 'order_cancelled',
                'subject_template': 'Ihre Bestellung wurde storniert - Bestellung #{{ order.id }}',
                'text_template': self.load_template_content('order_cancelled', 'txt'),
                'html_template': self.load_template_content('order_cancelled', 'html'),
                'is_active': True
            }
        ]

        # Add order summary template for Gerätewart
        order_summary_template = {
            'name': 'Bestellübersicht für Gerätewart',
            'template_type': 'order_summary',
            'subject_template': 'Bestellübersicht - {{ date_range }}',
            'text_template': self.load_template_content('order_summary', 'txt'),
            'html_template': self.load_template_content('order_summary', 'html'),
            'is_active': True
        }
        
        templates.append(order_summary_template)

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = EmailTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                # Update existing template if needed
                updated = False
                for field, value in template_data.items():
                    if getattr(template, field) != value:
                        setattr(template, field, value)
                        updated = True
                
                if updated:
                    template.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated template: {template.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Template already exists: {template.name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {len(templates)} templates '
                f'({created_count} created, {updated_count} updated)'
            )
        )
