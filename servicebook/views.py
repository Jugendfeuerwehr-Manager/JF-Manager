import crispy_forms
from crispy_forms.layout import Layout, Submit
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404

# Create your views here.
from django.views.generic import TemplateView, UpdateView, CreateView, DetailView
from django_tables2 import RequestConfig
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from inventory.forms import FormActionMixin
from members.models import Member
from members.selectors import get_members_list
from .filters import ServiceFilter
from .forms import ServiceForm
from .models import Service, Attendance
from .serializers import ServiceSerializer, AttendanceSerializer
from .tables import ServiceTable
from .selectors import get_services_list, get_top_lists_by_state, get_attandance_list, get_attendance_over_time_data


class ServiceTableView(LoginRequiredMixin, TemplateView):
    template_name = 'service_table.html'

    def get_queryset(self, **kwargs):
        return get_services_list()

    def get_context_data(self, **kwargs):
        context = super(ServiceTableView, self).get_context_data(**kwargs)
        filter = ServiceFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter.form.helper = ServiceTableFilterFormHelper()
        table = ServiceTable(filter.qs)
        RequestConfig(self.request).configure(table)
        context['filter'] = filter
        context['table'] = table
        context['services'] = get_services_list()
        context['top_present'] = get_top_lists_by_state('A')
        context['top_e'] = get_top_lists_by_state('E')
        context['top_f'] = get_top_lists_by_state('F')
        context['attendance_chart_data'] = get_attendance_over_time_data()
        return context


class ServiceTableFilterFormHelper(crispy_forms.helper.FormHelper):
    form_method = 'GET'
    form_class = 'form-inline'
    layout = Layout(
        'topic__contains',
        'operations_manager',
        'start',
        'end',
        Submit('submit', 'Filtern')
    )

class AttendanceJsonView(DetailView):
    model = Service
    http_method_names = ['post', 'get']

    def get(self, request, **kwargs):
        service = get_object_or_404(Service, pk=kwargs['pk'])
        attendees = Attendance.objects.filter(service=service)
        data = serializers.serialize('json', attendees)
        return HttpResponse(data, content_type='application/json')

    def post(self, request, **kwargs):
        member_pk = request.POST['member']
        state = request.POST['state']
        member = Member.objects.filter(pk=member_pk).first()
        service = Service.objects.filter(pk=self.kwargs['pk']).first()
        attendance = Attendance.objects.filter(person=member, service=service).first()

        if attendance is not None and state is not None:
            attendance.state = state
            attendance.save()
            return HttpResponse(status=200)
        else:
            attendance = Attendance.objects.create()
            attendance.state = state
            attendance.service = service
            attendance.person = member
            attendance.save()
            return HttpResponse(status=200)


class ServiceUpdateView(FormActionMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_edit.html'

    def get_success_url(self):
        return 'servicebook:home'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['members'] = get_members_list()
        return context

    def form_valid(self, form):
        item = form.save()
        item.save()
        return redirect('servicebook:home')


class ServiceCreateView(FormActionMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'service_edit.html'

    def get_success_url(self):
        return 'servicebook:home'

    def form_valid(self, form):
        item = form.save()
        item.save()
        return redirect('servicebook:edit', pk=item.pk)


############################ API ################################################

class ServiceViewSet(viewsets.ModelViewSet):
    """
    API Endpoint that allows Service to be viewed or edited
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_services_list()
    serializer_class = ServiceSerializer
    filterset_fields = '__all__'
    ordering_fields = ['start', 'end']
    search_fields = ['topic', 'description', 'events', 'place']



class AttandenceViewSet(viewsets.ModelViewSet):
    """
    API Endpoint that allows Attandance to be viewed or edited

    search is indexed to person name and lastname
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_attandance_list()
    serializer_class = AttendanceSerializer
    filterset_fields = '__all__'
    search_fields = ['person__name', 'person__lastname',]
    ordering_fields = ['state', 'id']

