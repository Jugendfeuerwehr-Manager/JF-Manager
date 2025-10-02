from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from inventory.models import Item
from inventory.models.stock import Stock
from members.forms import EventForm
from members.models import Member, Parent, Event, EventType, Attachment
from members.selectors import get_events_list
from servicebook.selectors import get_services_of_member, get_number_of_services

#
# Take a look at https://docs.djangoproject.com/en/3.0/topics/class-based-views/mixins/#using-formmixin-with-detailview
# to understand what happens here.
#

class MemberDetailView(LoginRequiredMixin, View):
    """
    A view class that handles member detail operations with required login.

    This view acts as a router between GET and POST requests:
    - GET requests are forwarded to MemberDisplayView for displaying member details
    - POST requests are forwarded to MemberEventView for handling member events

    Inherits from:
        LoginRequiredMixin: Ensures user is logged in before accessing view
        View: Base view class from Django

    Methods:
        get: Handles GET requests by delegating to MemberDisplayView
        post: Handles POST requests by delegating to MemberEventView
    """
    def get(self, request, *args, **kwargs):
        view = MemberDisplayView.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Handle attachment upload
        if request.POST.get('action') == 'add_attachment':
            return self.handle_attachment_upload(request, *args, **kwargs)
        
        # Handle attachment deletion
        if request.POST.get('action') == 'delete_attachment':
            return self.handle_attachment_delete(request, *args, **kwargs)
        
        # Default: handle member events
        view = MemberEventView.as_view()
        return view(request, *args, **kwargs)
    
    def handle_attachment_upload(self, request, *args, **kwargs):
        """Handle member attachment upload"""
        from django.shortcuts import get_object_or_404, redirect
        
        member = get_object_or_404(Member, pk=kwargs['pk'])
        
        # Check permissions
        if not request.user.has_perm('members.change_member'):
            messages.error(request, 'Sie haben keine Berechtigung, Anhänge hochzuladen.')
            return redirect('members:detail', pk=member.pk)
        
        # Get form data
        attachment_name = request.POST.get('attachment_name', '').strip()
        attachment_description = request.POST.get('attachment_description', '').strip()
        attachment_file = request.FILES.get('attachment_file')
        
        # Validation
        if not attachment_name:
            messages.error(request, 'Bitte geben Sie einen Namen für den Anhang ein.')
            return redirect('members:detail', pk=member.pk)
        
        if not attachment_file:
            messages.error(request, 'Bitte wählen Sie eine Datei aus.')
            return redirect('members:detail', pk=member.pk)
        
        # File validation
        max_size = 10 * 1024 * 1024  # 10MB
        allowed_extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif']
        file_extension = attachment_file.name.split('.')[-1].lower()
        
        if attachment_file.size > max_size:
            messages.error(request, 'Die Datei ist zu groß. Maximale Größe: 10MB')
            return redirect('members:detail', pk=member.pk)
        
        if file_extension not in allowed_extensions:
            messages.error(request, 'Dateityp nicht unterstützt. Erlaubte Formate: PDF, DOC, DOCX, JPG, PNG, GIF')
            return redirect('members:detail', pk=member.pk)
        
        try:
            # Create attachment
            content_type = ContentType.objects.get_for_model(Member)
            attachment = Attachment.objects.create(
                content_type=content_type,
                object_id=member.pk,
                name=attachment_name,
                description=attachment_description,
                file=attachment_file,
                uploaded_by=request.user
            )
            
            messages.success(request, f'Anhang "{attachment.name}" wurde erfolgreich hinzugefügt.')
        
        except Exception as e:
            messages.error(request, f'Fehler beim Hochladen des Anhangs: {str(e)}')
        
        return redirect('members:detail', pk=member.pk)

    def handle_attachment_delete(self, request, *args, **kwargs):
        """Handle member attachment deletion"""
        from django.shortcuts import get_object_or_404, redirect
        
        member = get_object_or_404(Member, pk=kwargs['pk'])
        
        # Check permissions
        if not request.user.has_perm('members.change_member'):
            messages.error(request, 'Sie haben keine Berechtigung, Anhänge zu löschen.')
            return redirect('members:detail', pk=member.pk)
        
        # Get attachment ID
        attachment_id = request.POST.get('attachment_id')
        if not attachment_id:
            messages.error(request, 'Anhang-ID nicht gefunden.')
            return redirect('members:detail', pk=member.pk)
        
        try:
            # Get attachment and verify it belongs to this member
            content_type = ContentType.objects.get_for_model(Member)
            attachment = get_object_or_404(
                Attachment,
                pk=attachment_id,
                content_type=content_type,
                object_id=member.pk
            )
            
            attachment_name = attachment.name
            attachment.delete()
            
            messages.success(request, f'Anhang "{attachment_name}" wurde erfolgreich gelöscht.')
        
        except Exception as e:
            messages.error(request, f'Fehler beim Löschen des Anhangs: {str(e)}')
        
        return redirect('members:detail', pk=member.pk)


class MemberDisplayView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    A view class for displaying detailed member information.

    This class implements a detail view for a Member instance, requiring both
    authentication and specific permissions to access. It displays member details
    along with related information such as parents, rented inventory items,
    service attendance records, and associated events.

    Attributes:
        model (Member): The model class this view displays
        template_name (str): The template used for rendering the view
        permission_required (str): The permission required to access this view

    Methods:
        get_context_data(**kwargs): Enhances the template context with additional
            member-related data including:
            - Associated parents
            - Rented inventory items
            - Service attendance records and statistics
            - Events the member is involved in
            - Event form for new entries

    Returns:
        dict: Enhanced context dictionary containing all member-related data
    """
    model = Member
    template_name = 'member_detail.html'
    permission_required = 'members.view_member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perms = self.request.user.get_all_permissions()
        obj = super().get_object()
        context['parents'] = Parent.objects.filter(children=obj.pk)
        context['inventory'] = Item.objects.filter(rented_by=obj.pk)
        # Bestände am persönlichen Lagerort (falls vorhanden)
        if obj.storage_location:
            context['member_location_stocks'] = Stock.objects.filter(location=obj.storage_location, quantity__gt=0).select_related('item', 'item_variant', 'item_variant__parent_item')
            # Pfad-Hierarchie für Breadcrumb
            path = []
            loc = obj.storage_location
            visited = set()
            while loc and loc.pk not in visited:
                path.append(loc)
                visited.add(loc.pk)
                loc = loc.parent
            context['storage_location_path'] = list(reversed(path))
        else:
            context['member_location_stocks'] = []
        context['attendances'] = get_services_of_member(member=obj).order_by('-service__start')
        context['n_missed_services'] = get_number_of_services(member=obj, state='F')
        context['n_attended_services'] = get_number_of_services(member=obj, state='A')
        context['n_excused_services'] = get_number_of_services(member=obj, state='E')
        context['events'] = get_events_list().filter(member=obj.pk)
        context['form'] = EventForm()
        
        # Qualifikationen und Sonderaufgaben hinzufügen
        try:
            from qualifications.models import Qualification, SpecialTask
            context['member_qualifications'] = Qualification.objects.filter(
                member=obj
            ).select_related('type').order_by('-date_acquired')
            context['member_special_tasks'] = SpecialTask.objects.filter(
                member=obj
            ).select_related('task').order_by('-start_date')
        except ImportError:
            # Falls qualifications App nicht installiert ist
            context['member_qualifications'] = []
            context['member_special_tasks'] = []
        
        # Member Anhänge hinzufügen
        content_type = ContentType.objects.get_for_model(Member)
        context['member_attachments'] = Attachment.objects.filter(
            content_type=content_type,
            object_id=obj.pk
        ).order_by('-uploaded_at')
        
        return context

class MemberEventView(LoginRequiredMixin, SingleObjectMixin, FormView):
    """
    A view for handling member events that requires user authentication.
    This view combines LoginRequiredMixin, SingleObjectMixin and FormView to handle
    the creation of events associated with a member. It supports both GET and POST
    requests, where POST requests create new events based on form data.
    Attributes:
        model (Member): The model class this view operates on
        template_name (str): The template used for rendering the view
        form_class (EventForm): The form class used for event creation
        permission_required (str): The required permission to access this view
    Methods:
        post(request, *args, **kwargs): 
            Handles POST requests for creating new events
            Returns HTTP 403 if user is not authenticated
        parse_date(date_str):
            Parses date strings in either ISO (YYYY-MM-DD) or German (DD.MM.YYYY) format
            Returns datetime object
            Raises ValueError if date string is invalid
        get_success_url():
            Returns the URL to redirect to after successful form submission
    Example:
        This view is typically used in URL patterns like:
        path('member/<int:pk>/', MemberEventView.as_view(), name='detail')
    """
    model = Member
    template_name = 'member_detail.html'
    form_class = EventForm
    permission_required = 'members.view_member'

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        
        self.object = self.get_object()
        form = self.get_form()
        
        if form.is_valid():
            event = Event()
            event.member = self.object
            event.notes = form.cleaned_data['notes']
            event.type = form.cleaned_data['type']
            
            # Handle date - it's already a date object from DateField
            event.datetime = form.cleaned_data['date']
            
            event.save()
        return super().post(request, *args, **kwargs)

    def parse_date(self, date_str):
        """Parse date string in ISO or German format."""
        for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD or DD.MM.YYYY")

    def get_success_url(self):
        return reverse('members:detail', kwargs={'pk': self.object.pk})