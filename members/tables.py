from datetime import date

from django.utils.safestring import mark_safe
import django_tables2 as tables
from django_tables2 import A
from servicebook.selectors import get_attandance_alert_by_member

from .models import Member, Parent


class MemberTable(tables.Table):

    edit = tables.LinkColumn('members:edit', text='', args=[A('pk')], orderable=False, empty_values=())
    delete = tables.LinkColumn('members:delete', text='', args=[A('pk')], orderable=False, empty_values=())
    name = tables.Column(attrs={'td': {'class': 'align-middle name'}}, orderable=True)
    lastname = tables.Column(attrs={'td': {'class': 'align-middle lastname'}}, orderable=True)
    status = tables.Column(attrs={'td': {'class': 'align-middle status'}}, orderable=True)
    group = tables.Column(attrs={'td': {'class': 'align-middle group'}}, orderable=True)
    birthday = tables.Column(attrs={'td': {'class': 'align-middle birthday'}}, orderable=True)

    def render_edit(self):
        return mark_safe('<i class="fas fa-edit"></i>')

    def render_delete(self):
        return mark_safe('<i class="fas fa-trash"></i>')

    def render_name(self, value, record):
        has_alert = '❗️' if get_attandance_alert_by_member(record, 5, 10) else ''

        url = record.get_absolute_url()
        return mark_safe('<a href="%s">%s %s</a>' % (url, has_alert, record.name,))

    def render_status(self, value, record):
        try:
            return mark_safe('<span style="color: %s">%s</span>' % (value.color, value.name,))
        except AttributeError:
            return mark_safe('<span>%s</span>' % value)

    def render_birthday(self, value, record):
        return (mark_safe('%s (<b><span class="age">%s</span></b> Jahre alt)' % (record.birthday, record.get_age())))

    class Meta:
        model = Member
        fields = ('name', 'lastname', 'status', 'group', 'birthday',)
        template_name = 'django_tables2/bootstrap4.html'
        attrs = {
            'class': 'table table-hover',
            'thead': {'class': 'bg-light'}
        }
        # Define order_by_field to match our view's parameter name
        order_by_field = 'sort'


class ParentTable(tables.Table):

    edit = tables.LinkColumn('members:parent_edit', text='', args=[A('pk')], orderable=False, empty_values=())
    delete = tables.LinkColumn('members:parent_delete', text='', args=[A('pk')], orderable=False, empty_values=())

    def render_edit(self):
        return '✏️'

    def render_delete(self):
        return '🗑'

    def render_mobile(self, value, record):
        return  mark_safe('<a href="tel:%s">%s</a>' % (record.mobile, record.mobile))

    def render_phone(self, value, record):
        return  mark_safe('<a href="tel:%s">%s</a>' % (record.phone, record.phone))

    def render_name(self, value, record):
        url = record.get_absolute_url()
        return mark_safe('<a href="%s">%s</a>' % (url, record.name,))


    class Meta:
        model = Parent
        fields = ('name', 'lastname', 'mobile', 'phone', 'email')
        template_name = 'django_tables2/bootstrap4.html'
