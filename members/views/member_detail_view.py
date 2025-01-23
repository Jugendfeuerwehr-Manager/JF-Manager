from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from inventory.models import Item
from members.forms import EventForm
from members.models import Member, Parent, Event, EventType
from members.selectors import get_events_list
from servicebook.selectors import get_services_of_member, get_number_of_services

#
# Take a look at https://docs.djangoproject.com/en/3.0/topics/class-based-views/mixins/#using-formmixin-with-detailview
# to understand what happens here.
#

class MemberDetailView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        view = MemberDisplayView.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = MemberEventView.as_view()
        return view(request, *args, **kwargs)


class MemberDisplayView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Member
    template_name = 'member_detail.html'
    permission_required = 'members.view_member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perms = self.request.user.get_all_permissions()
        obj = super().get_object()
        context['parents'] = Parent.objects.filter(children=obj.pk)
        context['inventory'] = Item.objects.filter(rented_by=obj.pk)
        context['attendances'] = get_services_of_member(member=obj)
        context['n_missed_services'] = get_number_of_services(member=obj, state='F')
        context['n_attended_services'] = get_number_of_services(member=obj, state='A')
        context['n_excused_services'] = get_number_of_services(member=obj, state='E')
        context['events'] = get_events_list().filter(member=obj.pk)
        context['form'] = EventForm()
        return context

class MemberEventView(LoginRequiredMixin, SingleObjectMixin, FormView):
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
            event.notes = form.data['notes']
            event.type = EventType.objects.get(pk=form.data['type'])
            
            # Handle both ISO and German date formats
            date_str = form.data['date']
            try:
                # First try ISO format
                event.datetime = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                try:
                    # Then try German format
                    event.datetime = datetime.strptime(date_str, '%d.%m.%Y')
                except ValueError:
                    raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD or DD.MM.YYYY")
            
            event.save()
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('members:detail', kwargs={'pk': self.object.pk})