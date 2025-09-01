from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView, ListView
from django.db.models import Q, Count, Case, When, IntegerField
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from django.urls import reverse

from ..models import Qualification, SpecialTask, QualificationType, SpecialTaskType
from ..forms import QualificationFilterForm, SpecialTaskFilterForm
from members.models import Member

User = get_user_model()


class QualificationsAdminView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Admin-Übersicht für Qualifikations- und Sonderaufgaben-Verwaltung"""
    template_name = 'qualifications/admin.html'
    permission_required = 'qualifications.manage_qualifications'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiken
        context.update({
            'qualification_types_count': QualificationType.objects.count(),
            'special_task_types_count': SpecialTaskType.objects.count(),
            'total_qualifications': Qualification.objects.count(),
            'total_special_tasks': SpecialTask.objects.count(),
            'expired_qualifications': Qualification.objects.filter(
                date_expires__lt=date.today()
            ).count(),
            'expiring_soon_count': len([
                q for q in Qualification.objects.all() if q.expires_soon()
            ]),
            'active_special_tasks': len([
                t for t in SpecialTask.objects.all() if t.is_active
            ]),
        })
        
        return context


class QualificationsDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard-Übersicht für Qualifikationen und Sonderaufgaben"""
    template_name = 'qualifications/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Basis-Querysets abhängig von Berechtigungen
        if user.has_perm('qualifications.view_all_qualifications'):
            # Admin kann alles sehen
            qualifications_qs = Qualification.objects.all()
            special_tasks_qs = SpecialTask.objects.all()
        elif user.has_perm('qualifications.view_qualification'):
            # Jugendleiter können Qualifikationen ihrer Mitglieder sehen
            # TODO: Hier könnte man eine Gruppenzugehörigkeit prüfen
            qualifications_qs = Qualification.objects.all()
            special_tasks_qs = SpecialTask.objects.all()
        else:
            # Mitglieder sehen nur ihre eigenen
            qualifications_qs = Qualification.objects.filter(
                Q(user=user) | Q(member__in=Member.objects.filter(user=user))
            )
            special_tasks_qs = SpecialTask.objects.filter(
                Q(user=user) | Q(member__in=Member.objects.filter(user=user))
            )

        # Statistiken
        today = date.today()
        soon_threshold = today + timedelta(days=30)
        
        context.update({
            'total_qualifications': qualifications_qs.count(),
            'expired_qualifications': qualifications_qs.filter(
                date_expires__lt=today
            ).count(),
            'expiring_qualifications': qualifications_qs.filter(
                date_expires__gte=today,
                date_expires__lte=soon_threshold
            ).count(),
            'active_special_tasks': special_tasks_qs.filter(
                Q(end_date__isnull=True) | Q(end_date__gt=today)
            ).count(),
            'completed_special_tasks': special_tasks_qs.filter(
                end_date__lte=today
            ).count(),
        })

        # Kürzlich erworbene Qualifikationen
        context['recent_qualifications'] = qualifications_qs.order_by('-date_acquired')[:5]
        
        # Bald ablaufende Qualifikationen
        context['expiring_qualifications_list'] = qualifications_qs.filter(
            date_expires__gte=today,
            date_expires__lte=soon_threshold
        ).order_by('date_expires')[:10]
        
        # Aktuelle Sonderaufgaben
        context['current_special_tasks'] = special_tasks_qs.filter(
            Q(end_date__isnull=True) | Q(end_date__gt=today)
        ).order_by('-start_date')[:10]

        return context


class QualificationsListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Liste aller Qualifikationen mit Filtermöglichkeiten"""
    model = Qualification
    template_name = 'qualifications/qualification_list.html'
    context_object_name = 'qualifications'
    paginate_by = 25
    permission_required = 'qualifications.view_qualification'

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Berechtigungsprüfung
        if not user.has_perm('qualifications.view_all_qualifications'):
            if user.has_perm('qualifications.view_qualification'):
                # Jugendleiter - alle Qualifikationen (oder spezifische Gruppe)
                pass  # TODO: Gruppenzugehörigkeit implementieren
            else:
                # Nur eigene Qualifikationen
                queryset = queryset.filter(
                    Q(user=user) | Q(member__in=Member.objects.filter(user=user))
                )

        # Filter anwenden
        form = QualificationFilterForm(self.request.GET)
        if form.is_valid():
            status = form.cleaned_data.get('status')
            qualification_type = form.cleaned_data.get('qualification_type')
            search = form.cleaned_data.get('search')

            if status:
                today = date.today()
                soon_threshold = today + timedelta(days=30)
                
                if status == 'active':
                    queryset = queryset.filter(
                        Q(date_expires__isnull=True) | Q(date_expires__gt=today)
                    )
                elif status == 'expiring':
                    queryset = queryset.filter(
                        date_expires__gte=today,
                        date_expires__lte=soon_threshold
                    )
                elif status == 'expired':
                    queryset = queryset.filter(date_expires__lt=today)

            if qualification_type:
                queryset = queryset.filter(type=qualification_type)

            if search:
                queryset = queryset.filter(
                    Q(user__username__icontains=search) |
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(member__name__icontains=search) |
                    Q(member__lastname__icontains=search) |
                    Q(type__name__icontains=search) |
                    Q(issued_by__icontains=search)
                )

        return queryset.select_related('type', 'user', 'member').order_by('-date_acquired')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = QualificationFilterForm(self.request.GET)
        return context


class SpecialTasksListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Liste aller Sonderaufgaben mit Filtermöglichkeiten"""
    model = SpecialTask
    template_name = 'qualifications/special_task_list.html'
    context_object_name = 'special_tasks'
    paginate_by = 25
    permission_required = 'qualifications.view_specialtask'

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Berechtigungsprüfung
        if not user.has_perm('qualifications.view_all_specialtasks'):
            if user.has_perm('qualifications.view_specialtask'):
                # Jugendleiter - alle Aufgaben (oder spezifische Gruppe)
                pass  # TODO: Gruppenzugehörigkeit implementieren
            else:
                # Nur eigene Aufgaben
                queryset = queryset.filter(
                    Q(user=user) | Q(member__in=Member.objects.filter(user=user))
                )

        # Filter anwenden
        form = SpecialTaskFilterForm(self.request.GET)
        if form.is_valid():
            status = form.cleaned_data.get('status')
            task_type = form.cleaned_data.get('task_type')
            search = form.cleaned_data.get('search')

            if status:
                today = date.today()
                
                if status == 'active':
                    queryset = queryset.filter(
                        Q(end_date__isnull=True) | Q(end_date__gt=today)
                    )
                elif status == 'completed':
                    queryset = queryset.filter(end_date__lte=today)

            if task_type:
                queryset = queryset.filter(task=task_type)

            if search:
                queryset = queryset.filter(
                    Q(user__username__icontains=search) |
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(member__name__icontains=search) |
                    Q(member__lastname__icontains=search) |
                    Q(task__name__icontains=search)
                )

        return queryset.select_related('task', 'user', 'member').order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = SpecialTaskFilterForm(self.request.GET)
        return context
