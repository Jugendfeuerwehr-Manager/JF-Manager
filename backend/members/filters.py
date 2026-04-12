import django_filters

from .models import Member, Parent


class MemberFilter(django_filters.FilterSet):

    class Meta:
        model = Member
        fields = {
            'name': ['contains'],
            'lastname': ['contains']
        }

class ParentFilter(django_filters.FilterSet):

    class Meta:
        model = Parent
        fields = {
            'name': ['contains'],
            'lastname': ['contains']
        }
