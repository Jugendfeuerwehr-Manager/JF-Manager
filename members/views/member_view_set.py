from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from members.selectors import get_members_list
from members.serializers import MemberSerializer


class MemberViewSet(viewsets.ModelViewSet):
    """
    API Endpoint that allows members to be viewed or edited
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_members_list()
    serializer_class = MemberSerializer
    filterset_fields = ['name','lastname','birthday','email','street','zip_code','city','phone','mobile','joined','identityCardNumber']
    search_fields = ['name','lastname','email','identityCardNumber']
    ordering_fields = ['id','name','lastname','birthday','joined']