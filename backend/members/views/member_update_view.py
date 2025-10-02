from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import UpdateView

from members.forms import MemberForm
from members.models import Member


class MemberUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'member_edit.html'
    permission_required = 'members.change_member'

    def get_success_url(self):
        return 'inventory:items'

    def form_valid(self, form):
        item = form.save()
        item.save()
        return redirect('members:index')