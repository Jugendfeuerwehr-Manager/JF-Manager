from django.core.management.base import BaseCommand
from orders.models import EmailTemplate


class Command(BaseCommand):
    help = 'Create default email templates for notifications'

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Bestellung erstellt',
                'template_type': 'order_created',
                'subject_template': 'Ihre Bestellung wurde erstellt - Bestellung #{{ order.id }}',
                'text_template': '''Hallo {{ customer_name }},

vielen Dank für Ihre Bestellung!

Bestelldetails:
- Bestell-ID: {{ order.id }}
- Erstellt am: {{ order.created_at|date:"d.m.Y H:i" }}
- Gesamtbetrag: {{ order.total_amount|floatformat:2 }} €

Wir werden Ihre Bestellung schnellstmöglich bearbeiten und Sie über den Status informieren.

Mit freundlichen Grüßen
Ihr Team''',
                'html_template': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #d61f1f;">Bestellung bestätigt</h2>
    
    <p>Hallo <strong>{{ customer_name }}</strong>,</p>
    
    <p>vielen Dank für Ihre Bestellung! Wir haben Ihre Bestellung erhalten und bearbeiten sie schnellstmöglich.</p>
    
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0;">Bestelldetails</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #dee2e6;"><strong>Bestell-ID:</strong></td>
                <td style="padding: 8px 0; border-bottom: 1px solid #dee2e6;">{{ order.id }}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #dee2e6;"><strong>Erstellt am:</strong></td>
                <td style="padding: 8px 0; border-bottom: 1px solid #dee2e6;">{{ order.created_at|date:"d.m.Y H:i" }}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0;"><strong>Gesamtbetrag:</strong></td>
                <td style="padding: 8px 0; font-size: 18px; color: #d61f1f;"><strong>{{ order.total_amount|floatformat:2 }} €</strong></td>
            </tr>
        </table>
    </div>
    
    <p>Wir werden Sie über den Bearbeitungsstatus Ihrer Bestellung informieren.</p>
    
    <p style="margin-top: 30px;">Mit freundlichen Grüßen<br>
    <strong>Ihr Team</strong></p>
</div>''',
                'is_active': True
            },
            {
                'name': 'Bestellung bestätigt',
                'template_type': 'order_confirmed',
                'subject_template': 'Ihre Bestellung wurde bestätigt - Bestellung #{{ order.id }}',
                'text_template': '''Hallo {{ customer_name }},

Ihre Bestellung wurde bestätigt und wird nun bearbeitet.

Bestelldetails:
- Bestell-ID: {{ order.id }}
- Status: Bestätigt
- Gesamtbetrag: {{ order.total_amount|floatformat:2 }} €

Sie erhalten eine weitere Benachrichtigung, sobald Ihre Bestellung versandt wurde.

Mit freundlichen Grüßen
Ihr Team''',
                'html_template': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #28a745;">Bestellung bestätigt</h2>
    
    <p>Hallo <strong>{{ customer_name }}</strong>,</p>
    
    <p>Ihre Bestellung wurde bestätigt und wird nun bearbeitet.</p>
    
    <div style="background-color: #d4edda; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
        <h3 style="margin-top: 0; color: #155724;">✓ Bestellung bestätigt</h3>
        <p style="margin-bottom: 0;">Bestell-ID: <strong>{{ order.id }}</strong><br>
        Gesamtbetrag: <strong>{{ order.total_amount|floatformat:2 }} €</strong></p>
    </div>
    
    <p>Sie erhalten eine weitere Benachrichtigung, sobald Ihre Bestellung versandt wurde.</p>
    
    <p style="margin-top: 30px;">Mit freundlichen Grüßen<br>
    <strong>Ihr Team</strong></p>
</div>''',
                'is_active': True
            },
            {
                'name': 'Bestellung versandt',
                'template_type': 'order_shipped',
                'subject_template': 'Ihre Bestellung wurde versandt - Bestellung #{{ order.id }}',
                'text_template': '''Hallo {{ customer_name }},

Ihre Bestellung wurde versandt!

Bestelldetails:
- Bestell-ID: {{ order.id }}
- Versanddatum: {{ order.shipped_at|date:"d.m.Y" }}
- Tracking-Nummer: {{ tracking_number|default:"Wird nachgereicht" }}

Ihre Bestellung sollte in den nächsten 2-3 Werktagen bei Ihnen ankommen.

Mit freundlichen Grüßen
Ihr Team''',
                'html_template': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #17a2b8;">Bestellung versandt</h2>
    
    <p>Hallo <strong>{{ customer_name }}</strong>,</p>
    
    <p>Ihre Bestellung wurde versandt! 📦</p>
    
    <div style="background-color: #d1ecf1; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #17a2b8;">
        <h3 style="margin-top: 0; color: #0c5460;">🚚 Versandinformationen</h3>
        <p><strong>Bestell-ID:</strong> {{ order.id }}<br>
        <strong>Versanddatum:</strong> {{ order.shipped_at|date:"d.m.Y" }}<br>
        {% if tracking_number %}
        <strong>Tracking-Nummer:</strong> {{ tracking_number }}
        {% else %}
        <strong>Tracking-Nummer:</strong> Wird nachgereicht
        {% endif %}</p>
    </div>
    
    <p>Ihre Bestellung sollte in den nächsten <strong>2-3 Werktagen</strong> bei Ihnen ankommen.</p>
    
    <p style="margin-top: 30px;">Mit freundlichen Grüßen<br>
    <strong>Ihr Team</strong></p>
</div>''',
                'is_active': True
            },
            {
                'name': 'Bestellung storniert',
                'template_type': 'order_cancelled',
                'subject_template': 'Ihre Bestellung wurde storniert - Bestellung #{{ order.id }}',
                'text_template': '''Hallo {{ customer_name }},

Ihre Bestellung wurde storniert.

Bestelldetails:
- Bestell-ID: {{ order.id }}
- Storniert am: {{ order.cancelled_at|date:"d.m.Y H:i" }}
- Grund: {{ cancellation_reason|default:"Nicht angegeben" }}

Falls Sie Fragen haben, kontaktieren Sie uns gerne.

Mit freundlichen Grüßen
Ihr Team''',
                'html_template': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #dc3545;">Bestellung storniert</h2>
    
    <p>Hallo <strong>{{ customer_name }}</strong>,</p>
    
    <p>Ihre Bestellung wurde storniert.</p>
    
    <div style="background-color: #f8d7da; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
        <h3 style="margin-top: 0; color: #721c24;">❌ Stornierung</h3>
        <p><strong>Bestell-ID:</strong> {{ order.id }}<br>
        <strong>Storniert am:</strong> {{ order.cancelled_at|date:"d.m.Y H:i" }}<br>
        {% if cancellation_reason %}
        <strong>Grund:</strong> {{ cancellation_reason }}
        {% endif %}</p>
    </div>
    
    <p>Falls Sie Fragen haben oder eine neue Bestellung aufgeben möchten, kontaktieren Sie uns gerne.</p>
    
    <p style="margin-top: 30px;">Mit freundlichen Grüßen<br>
    <strong>Ihr Team</strong></p>
</div>''',
                'is_active': True
            }
        ]

        # Add order summary template for Gerätewart
        order_summary_template = {
            'name': 'Bestellübersicht für Gerätewart',
            'template_type': 'order_summary',
            'subject_template': 'Bestellübersicht - {{ date_range }}',
            'text_template': '''Hallo {{ recipient_name }},

hier ist die Bestellübersicht für den Zeitraum {{ date_range }}:

OFFENE BESTELLUNGEN ({{ open_orders_count }}):
{% for order in open_orders %}
- Bestellung #{{ order.id }} ({{ order.member.name }} {{ order.member.lastname }})
  Bestellt am: {{ order.order_date|date:"d.m.Y" }}
  Status: {{ order.status }}
  Artikel: {{ order.items.count }}
{% endfor %}

KÜRZLICH BESTELLTE ARTIKEL:
{% for item in recent_items %}
- {{ item.item.name }}{% if item.size %} ({{ item.size }}){% endif %} 
  Menge: {{ item.quantity }}
  Status: {{ item.status }}
  Für: {{ item.order.member.name }} {{ item.order.member.lastname }}
{% endfor %}

ZUSAMMENFASSUNG:
- Gesamt offene Bestellungen: {{ open_orders_count }}
- Neue Bestellungen: {{ new_orders_count }}
- Versandete Artikel: {{ shipped_items_count }}
- Ausgelieferte Artikel: {{ delivered_items_count }}

Mit freundlichen Grüßen
JF-Manager System''',
            'html_template': '''<div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
    <h2 style="color: #d61f1f;">Bestellübersicht - {{ date_range }}</h2>
    
    <p>Hallo <strong>{{ recipient_name }}</strong>,</p>
    
    <p>hier ist die aktuelle Bestellübersicht:</p>
    
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #d61f1f;">📋 Offene Bestellungen ({{ open_orders_count }})</h3>
        {% if open_orders %}
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <thead>
                    <tr style="background-color: #e9ecef;">
                        <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Bestellung</th>
                        <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Mitglied</th>
                        <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Datum</th>
                        <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Artikel</th>
                    </tr>
                </thead>
                <tbody>
                    {% for order in open_orders %}
                    <tr>
                        <td style="padding: 8px; border: 1px solid #dee2e6;">#{{ order.id }}</td>
                        <td style="padding: 8px; border: 1px solid #dee2e6;">{{ order.member.name }} {{ order.member.lastname }}</td>
                        <td style="padding: 8px; border: 1px solid #dee2e6;">{{ order.order_date|date:"d.m.Y" }}</td>
                        <td style="padding: 8px; border: 1px solid #dee2e6;">{{ order.items.count }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p style="color: #28a745; font-style: italic;">Keine offenen Bestellungen! 🎉</p>
        {% endif %}
    </div>
    
    <div style="background-color: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #856404;">📦 Kürzlich bestellte Artikel</h3>
        {% if recent_items %}
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <thead>
                    <tr style="background-color: #ffeaa7;">
                        <th style="padding: 10px; border: 1px solid #f39c12; text-align: left;">Artikel</th>
                        <th style="padding: 10px; border: 1px solid #f39c12; text-align: left;">Menge</th>
                        <th style="padding: 10px; border: 1px solid #f39c12; text-align: left;">Status</th>
                        <th style="padding: 10px; border: 1px solid #f39c12; text-align: left;">Für</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in recent_items %}
                    <tr>
                        <td style="padding: 8px; border: 1px solid #f39c12;">{{ item.item.name }}{% if item.size %} ({{ item.size }}){% endif %}</td>
                        <td style="padding: 8px; border: 1px solid #f39c12;">{{ item.quantity }}</td>
                        <td style="padding: 8px; border: 1px solid #f39c12;">{{ item.status }}</td>
                        <td style="padding: 8px; border: 1px solid #f39c12;">{{ item.order.member.name }} {{ item.order.member.lastname }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <p style="color: #856404; font-style: italic;">Keine neuen Artikel in diesem Zeitraum.</p>
        {% endif %}
    </div>
    
    <div style="background-color: #d1ecf1; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #0c5460;">📊 Zusammenfassung</h3>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
            <div style="text-align: center; padding: 15px; background-color: #fff; border-radius: 5px;">
                <div style="font-size: 24px; font-weight: bold; color: #d61f1f;">{{ open_orders_count }}</div>
                <div style="font-size: 14px; color: #6c757d;">Offene Bestellungen</div>
            </div>
            <div style="text-align: center; padding: 15px; background-color: #fff; border-radius: 5px;">
                <div style="font-size: 24px; font-weight: bold; color: #28a745;">{{ new_orders_count }}</div>
                <div style="font-size: 14px; color: #6c757d;">Neue Bestellungen</div>
            </div>
            <div style="text-align: center; padding: 15px; background-color: #fff; border-radius: 5px;">
                <div style="font-size: 24px; font-weight: bold; color: #007bff;">{{ shipped_items_count }}</div>
                <div style="font-size: 14px; color: #6c757d;">Versendete Artikel</div>
            </div>
            <div style="text-align: center; padding: 15px; background-color: #fff; border-radius: 5px;">
                <div style="font-size: 24px; font-weight: bold; color: #6f42c1;">{{ delivered_items_count }}</div>
                <div style="font-size: 14px; color: #6c757d;">Ausgelieferte Artikel</div>
            </div>
        </div>
    </div>
    
    <p style="margin-top: 30px; color: #6c757d; font-size: 14px;">
        Diese Übersicht wurde automatisch generiert am {{ current_date|date:"d.m.Y H:i" }} Uhr.
    </p>
    
    <p style="color: #6c757d;">
        Mit freundlichen Grüßen<br>
        <strong>JF-Manager System</strong>
    </p>
</div>''',
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
