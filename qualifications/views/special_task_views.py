from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, View, ListView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q
from datetime import date

from ..models import SpecialTask, SpecialTaskType
from ..forms import SpecialTaskForm, SpecialTaskTypeForm, SpecialTaskEndForm
from members.models import Member
from users.models import CustomUser


class SpecialTaskCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Neue Sonderaufgabe erstellen"""
    model = SpecialTask
    form_class = SpecialTaskForm
    template_name = 'qualifications/special_task_form.html'
    permission_required = 'qualifications.add_specialtask'

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
        messages.success(self.request, 'Sonderaufgabe wurde erfolgreich erstellt.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('qualifications:special_task_detail', kwargs={'pk': self.object.pk})


class SpecialTaskUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Sonderaufgabe bearbeiten"""
    model = SpecialTask
    form_class = SpecialTaskForm
    template_name = 'qualifications/special_task_form.html'
    permission_required = 'qualifications.change_specialtask'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Berechtigung prüfen - nur eigene oder als Admin/Jugendleiter
        user = self.request.user
        if not user.has_perm('qualifications.manage_specialtasks'):
            if obj.user != user and not (obj.member and hasattr(user, 'member') and obj.member == user.member):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Sie haben keine Berechtigung, diese Sonderaufgabe zu bearbeiten.")
        
        return obj

    def form_valid(self, form):
        messages.success(self.request, 'Sonderaufgabe wurde erfolgreich aktualisiert.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('qualifications:special_task_detail', kwargs={'pk': self.object.pk})


class SpecialTaskDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Sonderaufgabe löschen"""
    model = SpecialTask
    template_name = 'qualifications/special_task_confirm_delete.html'
    permission_required = 'qualifications.delete_specialtask'
    success_url = reverse_lazy('qualifications:special_task_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Berechtigung prüfen - nur als Admin
        user = self.request.user
        if not user.has_perm('qualifications.manage_specialtasks'):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Sie haben keine Berechtigung, diese Sonderaufgabe zu löschen.")
        
        return obj

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Sonderaufgabe wurde erfolgreich gelöscht.')
        return super().delete(request, *args, **kwargs)


class SpecialTaskDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Sonderaufgabe-Details anzeigen"""
    model = SpecialTask
    template_name = 'qualifications/special_task_detail.html'
    permission_required = 'qualifications.view_specialtask'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Berechtigung prüfen
        user = self.request.user
        if not user.has_perm('qualifications.view_all_specialtasks'):
            if not user.has_perm('qualifications.manage_specialtasks'):
                if obj.user != user and not (obj.member and hasattr(user, 'member') and obj.member == user.member):
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied("Sie haben keine Berechtigung, diese Sonderaufgabe einzusehen.")
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Weitere Sonderaufgaben der gleichen Person
        person = self.object.get_person()
        if person:
            if self.object.user:
                related_tasks = SpecialTask.objects.filter(
                    user=person
                ).exclude(pk=self.object.pk).order_by('-start_date')[:5]
            else:
                related_tasks = SpecialTask.objects.filter(
                    member=person
                ).exclude(pk=self.object.pk).order_by('-start_date')[:5]
            
            context['related_tasks'] = related_tasks
        
        return context


class SpecialTaskEndView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Sonderaufgabe beenden"""
    permission_required = 'qualifications.change_specialtask'

    def get(self, request, pk):
        special_task = get_object_or_404(SpecialTask, pk=pk)
        
        # Berechtigung prüfen
        user = request.user
        if not user.has_perm('qualifications.manage_specialtasks'):
            if special_task.user != user and not (special_task.member and hasattr(user, 'member') and special_task.member == user.member):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Sie haben keine Berechtigung, diese Sonderaufgabe zu beenden.")
        
        # Prüfen, ob schon beendet
        if not special_task.is_active():
            messages.warning(request, 'Diese Sonderaufgabe ist bereits beendet.')
            return redirect('qualifications:special_task_detail', pk=pk)
        
        form = SpecialTaskEndForm(special_task=special_task)
        
        return render(request, 'qualifications/special_task_end_form.html', {
            'special_task': special_task,
            'form': form
        })

    def post(self, request, pk):
        special_task = get_object_or_404(SpecialTask, pk=pk)
        
        # Berechtigung prüfen
        user = request.user
        if not user.has_perm('qualifications.manage_specialtasks'):
            if special_task.user != user and not (special_task.member and hasattr(user, 'member') and special_task.member == user.member):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Sie haben keine Berechtigung, diese Sonderaufgabe zu beenden.")
        
        # Prüfen, ob schon beendet
        if not special_task.is_active():
            messages.warning(request, 'Diese Sonderaufgabe ist bereits beendet.')
            return redirect('qualifications:special_task_detail', pk=pk)
        
        form = SpecialTaskEndForm(request.POST, special_task=special_task)
        
        if form.is_valid():
            special_task.end_date = form.cleaned_data['end_date']
            
            # Notiz hinzufügen
            additional_note = form.cleaned_data.get('note')
            if additional_note:
                if special_task.note:
                    special_task.note += f"\n\nBeendet am {special_task.end_date}: {additional_note}"
                else:
                    special_task.note = f"Beendet am {special_task.end_date}: {additional_note}"
            
            special_task.save()
            messages.success(request, 'Sonderaufgabe wurde erfolgreich beendet.')
            return redirect('qualifications:special_task_detail', pk=pk)
        
        return render(request, 'qualifications/special_task_end_form.html', {
            'special_task': special_task,
            'form': form
        })


# SpecialTaskType Management Views

class SpecialTaskTypeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Liste aller Sonderaufgaben-Typen"""
    model = SpecialTaskType
    template_name = 'qualifications/special_task_type_list.html'
    context_object_name = 'special_task_types'
    permission_required = 'qualifications.view_specialtasktype'
    paginate_by = 20

    def get_queryset(self):
        queryset = SpecialTaskType.objects.all().order_by('name')
        
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


class SpecialTaskTypeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Neuen Sonderaufgaben-Typ erstellen"""
    model = SpecialTaskType
    form_class = SpecialTaskTypeForm
    template_name = 'qualifications/special_task_type_form.html'
    permission_required = 'qualifications.add_specialtasktype'
    success_url = reverse_lazy('qualifications:special_task_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Sonderaufgaben-Typ wurde erfolgreich erstellt.')
        return super().form_valid(form)


class SpecialTaskTypeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Sonderaufgaben-Typ bearbeiten"""
    model = SpecialTaskType
    form_class = SpecialTaskTypeForm
    template_name = 'qualifications/special_task_type_form.html'
    permission_required = 'qualifications.change_specialtasktype'
    success_url = reverse_lazy('qualifications:special_task_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Sonderaufgaben-Typ wurde erfolgreich aktualisiert.')
        return super().form_valid(form)


class SpecialTaskTypeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Sonderaufgaben-Typ löschen"""
    model = SpecialTaskType
    template_name = 'qualifications/special_task_type_confirm_delete.html'
    permission_required = 'qualifications.delete_specialtasktype'
    success_url = reverse_lazy('qualifications:special_task_type_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, f'Sonderaufgaben-Typ "{self.get_object().name}" wurde erfolgreich gelöscht.')
        return super().delete(request, *args, **kwargs)


# Import für render
from django.shortcuts import render
