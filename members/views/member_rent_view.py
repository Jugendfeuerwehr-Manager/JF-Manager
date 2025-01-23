from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.views.generic import DetailView

from inventory.models import Item
from members.models import Member


class MemberRentView(LoginRequiredMixin,PermissionRequiredMixin, DetailView):

    model = Member
    template_name = 'member_rent.html'
    permission_required = ('members.view_member',
                           'inventory.can_rent',
                           'inventory.view_item')

    http_method_names = ['post', 'get']

    def post(self, request, **kwargs):
        barcode = request.POST['barcode']
        item = Item.objects.filter(identifier2=barcode).first()

        if item is None:
            item = Item.objects.filter(identifier1=barcode).first()

        if barcode is not None and item is not None:

                item.rented_by = Member.objects.filter(pk=kwargs['pk']).first()
                item.save()
                return HttpResponse(status=200)
        else:
            return HttpResponse(status=404)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        return context