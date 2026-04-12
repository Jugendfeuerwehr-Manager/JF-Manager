import django_filters

from inventory.models import Item


class ItemFilter(django_filters.FilterSet):

    class Meta:
        model = Item
        fields = ['category', 'size', 'identifier1', 'identifier2', 'rented_by']
