import django_tables2 as tables
from django.utils.safestring import mark_safe
from django_tables2 import A
from .selectors import get_summary_of_attendances_per_service

from .models import Service


class ServiceTable(tables.Table):
    presence = tables.Column(verbose_name='Anwesenheit', empty_values=())
    edit = tables.LinkColumn('servicebook:edit', text='', args=[A('pk')], orderable=False, empty_values=())

    def render_edit(self):
        return '✏️'

    def render_presence(self, record):
        # Use pre-calculated attendance summary if available, otherwise fallback to selector
        if hasattr(record, 'attendance_summary'):
            state = record.attendance_summary
        else:
            state = get_summary_of_attendances_per_service(record)

        return mark_safe('<span class="badge badge-success">%s</span> <span class="badge badge-warning">%s</span> <span class="badge badge-danger">%s</span>' % (state['A'], state['E'], state['F']))

    def render_topic(self, value, record):
        url = record.get_absolute_url()
        has_events = '❗️' if record.has_events() else ''
        return mark_safe('<a href="%s">%s %s</a>' % (url, has_events, record.topic,))

    class Meta:
        model = Service
        fields = ('topic', 'operations_manager', 'start', 'end',)
        template_name = 'django_tables2/bootstrap4.html'

