from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q

from ..models import Qualification, QualificationType
from ..forms import QualificationForm, QualificationTypeForm
from members.models import Member
from users.models import CustomUser


class QualificationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Neue Qualifikation erstellen"""
    model = Qualification
    form_class = QualificationForm
    template_name = 'qualifications/qualification_form.html'
    permission_required = 'qualifications.add_qualification'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        # Vorauswahl basierend auf URL-Parametern
        user_id = self.request.GET.get('user')
        member_id = self.request.GET.get('member')
        
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                kwargs['initial_user'] = user
            except CustomUser.DoesNotExist:
                pass
        elif member_id:
            try:
                member = Member.objects.get(id=member_id)
                kwargs['initial_member'] = member
            except Member.DoesNotExist:
                pass
        
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Qualifikation wurde erfolgreich erstellt.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('qualifications:qualification_detail', kwargs={'pk': self.object.pk})


class QualificationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Qualifikation bearbeiten"""
    model = Qualification
    form_class = QualificationForm
    template_name = 'qualifications/qualification_form.html'
    permission_required = 'qualifications.change_qualification'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Berechtigung prüfen - nur eigene oder als Admin/Jugendleiter
        user = self.request.user
        if not user.has_perm('qualifications.manage_qualifications'):
            if obj.user != user and not (obj.member and hasattr(user, 'member') and obj.member == user.member):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Sie haben keine Berechtigung, diese Qualifikation zu bearbeiten.")
        
        return obj

    def form_valid(self, form):
        messages.success(self.request, 'Qualifikation wurde erfolgreich aktualisiert.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('qualifications:qualification_detail', kwargs={'pk': self.object.pk})


class QualificationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Qualifikation löschen"""
    model = Qualification
    template_name = 'qualifications/qualification_confirm_delete.html'
    permission_required = 'qualifications.delete_qualification'
    success_url = reverse_lazy('qualifications:qualification_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Berechtigung prüfen - nur als Admin
        user = self.request.user
        if not user.has_perm('qualifications.manage_qualifications'):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Sie haben keine Berechtigung, diese Qualifikation zu löschen.")
        
        return obj

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Qualifikation wurde erfolgreich gelöscht.')
        return super().delete(request, *args, **kwargs)


class QualificationDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Qualifikation-Details anzeigen"""
    model = Qualification
    template_name = 'qualifications/qualification_detail.html'
    permission_required = 'qualifications.view_qualification'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Berechtigung prüfen
        user = self.request.user
        if not user.has_perm('qualifications.view_all_qualifications'):
            if not user.has_perm('qualifications.manage_qualifications'):
                if obj.user != user and not (obj.member and hasattr(user, 'member') and obj.member == user.member):
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied("Sie haben keine Berechtigung, diese Qualifikation einzusehen.")
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Weitere Qualifikationen der gleichen Person
        person = self.object.get_person()
        if person:
            if self.object.user:
                related_qualifications = Qualification.objects.filter(
                    user=person
                ).exclude(pk=self.object.pk).order_by('-date_acquired')[:5]
            else:
                related_qualifications = Qualification.objects.filter(
                    member=person
                ).exclude(pk=self.object.pk).order_by('-date_acquired')[:5]
            
            context['related_qualifications'] = related_qualifications
        
        return context


# AJAX Views

def qualification_type_details(request, pk):
    """AJAX: Details eines Qualifikationstyps abrufen"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Nicht autorisiert'}, status=401)
    
    try:
        qualification_type = QualificationType.objects.get(pk=pk)
        return JsonResponse({
            'name': qualification_type.name,
            'expires': qualification_type.expires,
            'validity_period': qualification_type.validity_period,
            'description': qualification_type.description,
        })
    except QualificationType.DoesNotExist:
        return JsonResponse({'error': 'Qualifikationstyp nicht gefunden'}, status=404)


def calculate_expiry_date(request):
    """AJAX: Ablaufdatum basierend auf Typ und Erwerbsdatum berechnen"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Nicht autorisiert'}, status=401)
    
    try:
        type_id = request.GET.get('type_id')
        date_acquired = request.GET.get('date_acquired')
        
        if not type_id or not date_acquired:
            return JsonResponse({'error': 'Fehlende Parameter'}, status=400)
        
        qualification_type = QualificationType.objects.get(pk=type_id)
        
        if not qualification_type.expires or not qualification_type.validity_period:
            return JsonResponse({'expires': False})
        
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        acquired_date = datetime.strptime(date_acquired, '%Y-%m-%d').date()
        expiry_date = acquired_date + relativedelta(months=qualification_type.validity_period)
        
        return JsonResponse({
            'expires': True,
            'expiry_date': expiry_date.strftime('%Y-%m-%d')
        })
        
    except (QualificationType.DoesNotExist, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)


# QualificationType Management Views

class QualificationTypeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Liste aller Qualifikationstypen"""
    model = QualificationType
    template_name = 'qualifications/qualification_type_list.html'
    context_object_name = 'qualification_types'
    permission_required = 'qualifications.view_qualificationtype'
    paginate_by = 20

    def get_queryset(self):
        queryset = QualificationType.objects.all().order_by('name')
        
        # Suchfilter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context


class QualificationTypeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Neuen Qualifikationstyp erstellen"""
    model = QualificationType
    form_class = QualificationTypeForm
    template_name = 'qualifications/qualification_type_form.html'
    permission_required = 'qualifications.add_qualificationtype'
    success_url = reverse_lazy('qualifications:qualification_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Qualifikationstyp wurde erfolgreich erstellt.')
        return super().form_valid(form)


class QualificationTypeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Qualifikationstyp bearbeiten"""
    model = QualificationType
    form_class = QualificationTypeForm
    template_name = 'qualifications/qualification_type_form.html'
    permission_required = 'qualifications.change_qualificationtype'
    success_url = reverse_lazy('qualifications:qualification_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Qualifikationstyp wurde erfolgreich aktualisiert.')
        return super().form_valid(form)


class QualificationTypeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Qualifikationstyp löschen"""
    model = QualificationType
    template_name = 'qualifications/qualification_type_confirm_delete.html'
    permission_required = 'qualifications.delete_qualificationtype'
    success_url = reverse_lazy('qualifications:qualification_type_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, f'Qualifikationstyp "{self.get_object().name}" wurde erfolgreich gelöscht.')
        return super().delete(request, *args, **kwargs)
