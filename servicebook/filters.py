import django_filters

from .models import Service


class ServiceFilter(django_filters.FilterSet):

    class Meta:
        model = Service
        fields = {
            'topic': ['contains'],
            'operations_manager': ['exact'],
            'start': ['exact'],
            'end': ['exact'],
        }
