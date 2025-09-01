from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from members.models import Member
from members.renderers import MemberExcelRenderer
from members.resources import MemberResource
from members.serializers import MemberSerializer


class MemberExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Export von Mitgliederdaten als Excel - nur für berechtigte Benutzer"""
    permission_required = 'members.view_member'

    def get(self, request):
        person_resource = MemberResource()
        dataset = person_resource.export()
        response = HttpResponse(dataset.xlsx, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="members.xlsx"'
        return response


class MemberExcelApiView(APIView):
    """API Endpoint für Mitglieder-Export als Excel - nur für authentifizierte und berechtigte Benutzer"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    renderer_classes = [MemberExcelRenderer]
    queryset = Member.objects.all()
    
    def get(self, request, format=None):
        # Zusätzliche Berechtigungsprüfung
        if not request.user.has_perm('members.view_member'):
            return Response({'error': 'Keine Berechtigung für Mitglieder-Export'}, status=403)
            
        # Queryset basierend auf Berechtigungen einschränken
        queryset = Member.objects.all()
        
        # Zusätzliche Einschränkungen basierend auf Gruppenzugehörigkeit können hier implementiert werden
        # if not request.user.has_perm('members.view_all_members'):
        #     # Nur Mitglieder der eigenen Gruppe
        #     queryset = queryset.filter(group__in=request.user.groups.all())
        
        serializer = MemberSerializer(queryset, many=True)
        return Response(serializer.data)
