import django_tables2 as tables
from django_tables2.utils import A
from django.utils.html import format_html
from django.urls import reverse

from .models import Order, OrderItem


class OrderTable(tables.Table):
    """Tabelle für Bestellungen"""
    
    member = tables.Column(
        verbose_name='Mitglied',
        empty_values=()
    )
    
    order_date = tables.DateTimeColumn(
        format='d.m.Y H:i',
        verbose_name='Bestelldatum'
    )
    
    ordered_by = tables.Column(
        accessor='ordered_by__get_full_name',
        verbose_name='Bestellt von'
    )
    
    items_count = tables.Column(
        empty_values=(),
        verbose_name='Artikel'
    )
    
    status_summary = tables.Column(
        empty_values=(),
        verbose_name='Status',
        orderable=False
    )
    
    actions = tables.Column(
        empty_values=(),
        verbose_name='Aktionen',
        orderable=False
    )

    class Meta:
        model = Order
        template_name = 'django_tables2/bootstrap4.html'
        fields = ('member', 'order_date', 'ordered_by', 'items_count', 'status_summary', 'actions')
        attrs = {
            'class': 'table table-striped table-hover',
            'thead': {
                'class': 'thead-light'
            }
        }

    def render_member(self, record):
        """Render member with link to order detail"""
        url = reverse('orders:detail', args=[record.pk])
        return format_html(
            '<a href="{}" class="text-decoration-none"><strong>{}</strong></a>',
            url,
            record.member.get_full_name()
        )

    def render_items_count(self, record):
        """Anzahl der Artikel in der Bestellung"""
        count = record.items.count()
        return format_html('<span class="badge badge-info">{}</span>', count)

    def render_status_summary(self, record):
        """Status-Übersicht als farbige Badges"""
        from django.utils.safestring import mark_safe
        
        status_counts = {}
        for item in record.items.all():
            status = item.status.name
            color = item.status.color
            if status not in status_counts:
                status_counts[status] = {'count': 0, 'color': color}
            status_counts[status]['count'] += 1
        
        badges = []
        for status, data in status_counts.items():
            badges.append(format_html(
                '<span class="badge badge-sm mr-1" style="background-color: {}; color: white;">{}: {}</span>',
                data['color'],
                status,
                data['count']
            ))
        
        return mark_safe(''.join(badges))

    def render_actions(self, record):
        """Aktionsbuttons"""
        from django.utils.safestring import mark_safe
        
        detail_url = reverse('orders:detail', args=[record.pk])
        
        buttons = []
        buttons.append(format_html(
            '<a href="{}" class="btn btn-sm btn-outline-primary" title="Details anzeigen">'
            '<i class="fas fa-eye"></i></a>',
            detail_url
        ))
        
        return mark_safe(f'<div class="btn-group" role="group">{"".join(buttons)}</div>')


class OrderItemTable(tables.Table):
    """Tabelle für Bestellartikel"""
    
    item = tables.Column(
        accessor='item__name',
        verbose_name='Artikel'
    )
    
    category = tables.Column(
        accessor='item__category',
        verbose_name='Kategorie'
    )
    
    size = tables.Column(
        verbose_name='Größe',
        empty_values=('',)
    )
    
    quantity = tables.Column(
        verbose_name='Anzahl'
    )
    
    status = tables.Column(
        verbose_name='Status'
    )
    
    received_date = tables.DateTimeColumn(
        format='d.m.Y H:i',
        verbose_name='Eingangsdatum'
    )
    
    delivered_date = tables.DateTimeColumn(
        format='d.m.Y H:i',
        verbose_name='Ausgabedatum'
    )
    
    actions = tables.Column(
        empty_values=(),
        verbose_name='Aktionen',
        orderable=False
    )

    class Meta:
        model = OrderItem
        template_name = 'django_tables2/bootstrap4.html'
        fields = ('item', 'category', 'size', 'quantity', 'status', 'received_date', 'delivered_date', 'actions')
        attrs = {
            'class': 'table table-striped table-sm',
            'thead': {
                'class': 'thead-light'
            }
        }

    def render_size(self, value):
        """Größe anzeigen oder '-' wenn leer"""
        return value or '-'

    def render_status(self, record):
        """Status als farbiger Badge"""
        return format_html(
            '<span class="badge" style="background-color: {}; color: white;">{}</span>',
            record.status.color,
            record.status.name
        )

    def render_received_date(self, value):
        """Eingangsdatum oder '-'"""
        return value.strftime('%d.%m.%Y %H:%M') if value else '-'

    def render_delivered_date(self, value):
        """Ausgabedatum oder '-'"""
        return value.strftime('%d.%m.%Y %H:%M') if value else '-'

    def render_actions(self, record):
        """Aktionsbuttons für Bestellartikel"""
        buttons = []
        
        # Status ändern Button (nur für berechtigte Benutzer)
        update_url = reverse('orders:update_item_status', args=[record.order.pk, record.pk])
        buttons.append(format_html(
            '<a href="{}" class="btn btn-sm btn-outline-warning" title="Status ändern">'
            '<i class="fas fa-edit"></i></a>',
            update_url
        ))
        
        return format_html('<div class="btn-group" role="group">{}</div>', ''.join(buttons))
