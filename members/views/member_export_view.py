from django.http import HttpResponse
from django.views import View
from rest_framework.response import Response
from rest_framework.views import APIView

from members.models import Member
from members.renderers import MemberExcelRenderer
from members.resources import MemberResource
from members.serializers import MemberSerializer


class MemberExportView(View):

        def get(self, request):
            person_resource = MemberResource()
            dataset = person_resource.export()
            response = HttpResponse(dataset.xlsx, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename="members.xlsx"'
            return response


class MemberExcelApiView(APIView):
    renderer_classes = [MemberExcelRenderer]
    queryset = Member.objects.all()
    def get(self, request, format=None):
        queryset = Member.objects.all()  # Adjust queryset as needed
        serializer = MemberSerializer(queryset, many=True)
        return Response(serializer.data)
