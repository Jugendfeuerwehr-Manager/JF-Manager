from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from datetime import date, timedelta

# Import models from different apps
from members.models import Member
from inventory.models import Item, Transaction, Stock
from qualifications.models import Qualification, SpecialTask, QualificationType, SpecialTaskType
from orders.models import Order, OrderItem
from servicebook.models import Service

User = get_user_model()


class DashboardView(LoginRequiredMixin, TemplateView):
    """Zentrale Dashboard-Startseite für die JF-Manager Verwaltungsoberfläche"""
    template_name = 'dashboard/main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()
        
        # Basis-Statistiken für alle Benutzer
        stats = {
            'total_members': Member.objects.count(),
            'total_items': Item.objects.count(),
            'total_qualifications': Qualification.objects.count(),
            'total_special_tasks': SpecialTask.objects.count(),
        }

        # Erweiterte Statistiken je nach Berechtigung
        if user.has_perm('members.view_member'):
            # Da wir nicht wissen, welche Status als "aktiv" gelten, zeigen wir nur die Gesamtzahl
            stats.update({
                'active_members': Member.objects.exclude(status__isnull=True).count(),
                'total_members_with_status': Member.objects.filter(status__isnull=False).count(),
            })

        if user.has_perm('inventory.view_item'):
            # Anstatt nach einem quantity Feld zu suchen, prüfen wir Stock-Einträge
            low_stock_count = 0
            for stock in Stock.objects.select_related('item', 'item_variant'):
                if stock.quantity <= 5:
                    low_stock_count += 1
            
            stats.update({
                'low_stock_items': low_stock_count,
                'recent_transactions': Transaction.objects.filter(
                    date__gte=today - timedelta(days=7)
                ).count(),
            })

        if user.has_perm('qualifications.view_qualification'):
            expired_qualifications = Qualification.objects.filter(
                date_expires__lt=today
            ).count()
            expiring_soon = Qualification.objects.filter(
                date_expires__gte=today,
                date_expires__lte=today + timedelta(days=30)
            ).count()
            
            stats.update({
                'expired_qualifications': expired_qualifications,
                'expiring_qualifications': expiring_soon,
                'active_special_tasks': SpecialTask.objects.filter(
                    Q(end_date__isnull=True) | Q(end_date__gt=today)
                ).count(),
            })

        if user.has_perm('orders.view_order'):
            # Zähle offene Bestellungen (als alle die noch nicht abgeschlossen sind)
            total_orders = Order.objects.count()
            recent_orders = Order.objects.filter(
                order_date__gte=today - timedelta(days=30)
            ).count()
            
            stats.update({
                'pending_orders': total_orders,
                'processing_orders': recent_orders,
            })

        if user.has_perm('servicebook.view_service'):
            stats.update({
                'recent_service_entries': Service.objects.filter(
                    start__gte=today - timedelta(days=30)
                ).count(),
            })

        context['stats'] = stats

        # Kürzliche Aktivitäten (falls berechtigt)
        activities = []
        
        if user.has_perm('qualifications.view_qualification'):
            recent_qualifications = Qualification.objects.select_related(
                'type', 'user', 'member'
            ).order_by('-date_acquired')[:5]
            activities.extend([
                {
                    'type': 'qualification',
                    'icon': 'fas fa-certificate',
                    'title': f'Neue Qualifikation: {q.type.name}',
                    'description': f'{q.get_person_name()} - {q.date_acquired}',
                    'date': q.date_acquired,
                    'url': '/qualifications/'
                }
                for q in recent_qualifications
            ])

        if user.has_perm('inventory.view_transaction'):
            recent_transactions = Transaction.objects.select_related(
                'item', 'user'
            ).order_by('-date')[:5]
            activities.extend([
                {
                    'type': 'transaction',
                    'icon': 'fas fa-exchange-alt',
                    'title': f'{t.get_transaction_type_display()}: {t.get_item_name()}',
                    'description': f'Menge: {t.quantity} - {t.user.get_full_name() if t.user else "Unbekannt"}',
                    'date': t.date.date(),
                    'url': '/inventory/'
                }
                for t in recent_transactions
            ])

        # Aktivitäten nach Datum sortieren
        activities.sort(key=lambda x: x['date'], reverse=True)
        context['recent_activities'] = activities[:10]

        # Wichtige Erinnerungen
        reminders = []
        
        if user.has_perm('qualifications.view_qualification'):
            expiring_quals = Qualification.objects.filter(
                date_expires__gte=today,
                date_expires__lte=today + timedelta(days=30)
            ).select_related('type', 'user', 'member').order_by('date_expires')[:5]
            
            reminders.extend([
                {
                    'type': 'warning',
                    'icon': 'fas fa-exclamation-triangle',
                    'title': f'Qualifikation läuft ab: {q.type.name}',
                    'description': f'{q.get_person_name()} - Ablauf: {q.date_expires}',
                    'url': '/qualifications/'
                }
                for q in expiring_quals
            ])

        if user.has_perm('inventory.view_item'):
            low_stock_items = Stock.objects.filter(quantity__lte=5).select_related('item', 'item_variant')[:5]
            reminders.extend([
                {
                    'type': 'danger',
                    'icon': 'fas fa-exclamation-circle',
                    'title': f'Niedriger Lagerbestand: {stock.get_item_name()}',
                    'description': f'Aktuell: {stock.quantity} im {stock.location.name}',
                    'url': '/inventory/'
                }
                for stock in low_stock_items
            ])

        context['reminders'] = reminders

        # Verfügbare Module basierend auf Berechtigungen
        modules = []
        
        if user.has_perm('members.view_member'):
            modules.append({
                'name': 'Mitglieder',
                'description': 'Mitgliederverwaltung und -organisation',
                'icon': 'fas fa-users',
                'color': 'primary',
                'url': '/members/',
                'count': stats.get('total_members', 0)
            })

        if user.has_perm('inventory.view_item'):
            modules.append({
                'name': 'Inventar',
                'description': 'Ausrüstung und Materialverwaltung',
                'icon': 'fas fa-boxes',
                'color': 'success',
                'url': '/inventory/',
                'count': stats.get('total_items', 0)
            })

        if user.has_perm('qualifications.view_qualification'):
            modules.append({
                'name': 'Qualifikationen',
                'description': 'Ausbildungen und Sonderaufgaben',
                'icon': 'fas fa-certificate',
                'color': 'info',
                'url': '/qualifications/',
                'count': stats.get('total_qualifications', 0)
            })

        if user.has_perm('orders.view_order'):
            modules.append({
                'name': 'Bestellungen',
                'description': 'Bestellverwaltung und -verfolgung',
                'icon': 'fas fa-shopping-cart',
                'color': 'warning',
                'url': '/orders/',
                'count': stats.get('pending_orders', 0)
            })

        if user.has_perm('servicebook.view_service'):
            modules.append({
                'name': 'Dienstbuch',
                'description': 'Dienste und Aktivitäten erfassen',
                'icon': 'fas fa-book',
                'color': 'secondary',
                'url': '/servicebook/',
                'count': stats.get('recent_service_entries', 0)
            })

        context['modules'] = modules

        # Schnellzugriff-Daten
        if user.has_perm('qualifications.view_qualification'):
            # Kürzlich erworbene Qualifikationen
            context['recent_qualifications'] = Qualification.objects.select_related(
                'type', 'user', 'member'
            ).order_by('-date_acquired')[:5]
            
            # Aktuelle Sonderaufgaben
            context['current_special_tasks'] = SpecialTask.objects.select_related(
                'task', 'user', 'member'
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=today)
            ).order_by('-start_date')[:5]

        return context
