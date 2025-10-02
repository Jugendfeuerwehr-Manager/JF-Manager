from django.utils.safestring import mark_safe
import django_tables2 as tables
from django_tables2 import A

from inventory.models import Item


class ItemTable(tables.Table):
    edit = tables.LinkColumn('inventory:item_edit', text='', args=[A('pk')], orderable=False, empty_values=())
    delete = tables.LinkColumn('inventory:item_delete', text='', args=[A('pk')], orderable=False, empty_values=())


    def render_edit(self):
        return '✏️'

    def render_delete(self):
        return '🗑   '

    def render_category(self, value, record):
        url = record.get_absolute_url()
        return mark_safe('<a href="%s">%s</a>' % (url, record.category))

    class Meta:
        model = Item
        fields = ('category', 'size', 'identifier1', 'identifier2', 'rented_by')
        template_name = 'django_tables2/bootstrap4.html'
