from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import FormView
from django.core.exceptions import PermissionDenied

from ..permissions import SettingsPermissionMixin, CategoryPermissionMixin


class BaseSettingsFormView(LoginRequiredMixin, SettingsPermissionMixin, CategoryPermissionMixin, FormView):
    """
    Basis-View für Einstellungsformulare
    """
    template_name = 'settings_manager/settings_form.html'
    success_url = reverse_lazy('settings_manager:overview')
    
    # Diese Attribute müssen in Unterklassen definiert werden
    category_code = None
    category_title = None
    form_class = None
    
    def dispatch(self, request, *args, **kwargs):
        # Prüfe View-Berechtigung
        if not self.check_category_permission(request.user, self.category_code, 'view'):
            raise PermissionDenied(f"Sie haben keine Berechtigung, {self.category_title} einzusehen.")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category_title'] = self.category_title
        context['category_code'] = self.category_code
        context['can_edit'] = self.check_category_permission(
            self.request.user, self.category_code, 'change'
        )
        return context
    
    def form_valid(self, form):
        # Prüfe Änderungsberechtigung
        if not self.check_category_permission(self.request.user, self.category_code, 'change'):
            raise PermissionDenied(f"Sie haben keine Berechtigung, {self.category_title} zu ändern.")
        
        # Speichere die Einstellungen
        if form.save():
            messages.success(
                self.request,
                f'{self.category_title} wurden erfolgreich gespeichert.'
            )
        else:
            messages.error(
                self.request,
                f'Fehler beim Speichern der {self.category_title}.'
            )
        
        return super().form_valid(form)