from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse

from ..permissions import CategoryPermissionMixin
from ..forms import (
    GeneralSettingsForm,
    EmailSettingsForm,
    MemberSettingsForm,
    ServiceSettingsForm,
    OrderSettingsForm
)


class TabbedSettingsView(LoginRequiredMixin, CategoryPermissionMixin, TemplateView):
    """
    Tabbed Layout für alle Einstellungen
    """
    template_name = 'settings_manager/tabbed_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Definiere alle Tabs mit ihren Formularen
        tabs = []
        
        # Allgemeine Einstellungen
        if self.check_category_permission(self.request.user, 'general', 'view'):
            tabs.append({
                'id': 'general',
                'title': 'Allgemein',
                'icon': 'fas fa-cogs',
                'form': GeneralSettingsForm(tabbed_layout=True),
                'can_edit': self.check_category_permission(self.request.user, 'general', 'change')
            })
        
        # E-Mail Einstellungen
        if self.check_category_permission(self.request.user, 'email', 'view'):
            tabs.append({
                'id': 'email',
                'title': 'E-Mail',
                'icon': 'fas fa-envelope',
                'form': EmailSettingsForm(tabbed_layout=True),
                'can_edit': self.check_category_permission(self.request.user, 'email', 'change')
            })
        
        # Mitglieder Einstellungen
        if self.check_category_permission(self.request.user, 'member', 'view'):
            tabs.append({
                'id': 'member',
                'title': 'Mitglieder',
                'icon': 'fas fa-users',
                'form': MemberSettingsForm(tabbed_layout=True),
                'can_edit': self.check_category_permission(self.request.user, 'member', 'change')
            })
        
        # Dienst Einstellungen
        if self.check_category_permission(self.request.user, 'service', 'view'):
            tabs.append({
                'id': 'service',
                'title': 'Dienste',
                'icon': 'fas fa-calendar-alt',
                'form': ServiceSettingsForm(tabbed_layout=True),
                'can_edit': self.check_category_permission(self.request.user, 'service', 'change')
            })
        
        # Bestell Einstellungen
        if self.check_category_permission(self.request.user, 'order', 'view'):
            tabs.append({
                'id': 'order',
                'title': 'Bestellungen',
                'icon': 'fas fa-shopping-cart',
                'form': OrderSettingsForm(tabbed_layout=True),
                'can_edit': self.check_category_permission(self.request.user, 'order', 'change')
            })
        
        context['tabs'] = tabs
        return context
    
    def post(self, request, *args, **kwargs):
        """
        Handle AJAX form submissions for specific tabs
        """
        tab_id = request.POST.get('tab_id')
        
        if not tab_id:
            return JsonResponse({'success': False, 'error': 'Tab ID fehlt'})
        
        # Prüfe Berechtigungen
        if not self.check_category_permission(request.user, tab_id, 'change'):
            return JsonResponse({'success': False, 'error': 'Keine Berechtigung zum Ändern'})
        
        # Bestimme das richtige Formular basierend auf tab_id
        form_class_map = {
            'general': GeneralSettingsForm,
            'email': EmailSettingsForm,
            'member': MemberSettingsForm,
            'service': ServiceSettingsForm,
            'order': OrderSettingsForm,
        }
        
        form_class = form_class_map.get(tab_id)
        if not form_class:
            return JsonResponse({'success': False, 'error': 'Unbekannte Tab ID'})
        
        form = form_class(request.POST)
        
        if form.is_valid():
            if form.save():
                return JsonResponse({
                    'success': True, 
                    'message': 'Einstellungen erfolgreich gespeichert'
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'error': 'Fehler beim Speichern der Einstellungen'
                })
        else:
            # Form-Fehler zurückgeben
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = error_list
            return JsonResponse({
                'success': False, 
                'error': 'Formular enthält Fehler',
                'form_errors': errors
            })