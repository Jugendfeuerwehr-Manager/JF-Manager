from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView

from members.forms import MemberForm
from members.models import Member


class MemberCreateView( PermissionRequiredMixin, CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'member_edit.html'
    permission_required = 'members.add_member'

    def get_success_url(self):
        return 'members:member'

    def form_valid(self, form):
        item = form.save()
        item.save()
        return redirect('members:index')