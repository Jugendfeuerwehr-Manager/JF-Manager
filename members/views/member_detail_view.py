from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from inventory.models import Item
from inventory.models.stock import Stock
from members.forms import EventForm
from members.models import Member, Parent, Event, EventType
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
        view = MemberEventView.as_view()
        return view(request, *args, **kwargs)


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