from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from members.selectors import get_parent_list
from members.serializers import ParentSerializer


class ParentViewSet(viewsets.ModelViewSet):
    """
    API Endpoint that allows parents to be viewed or edited

    The search parameter searches in Name, Lastname, both mail addresses and the names of the children.
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_parent_list()
    serializer_class = ParentSerializer
    ordering_fields = ['id','name','lastname']
    search_fields = ['name', 'lastname', 'email', 'email2', 'children__name', 'children__lastname']