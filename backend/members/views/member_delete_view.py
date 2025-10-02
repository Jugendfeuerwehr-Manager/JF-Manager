from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from members.models import Member


class MemberDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Member
    template_name = 'member_confirm_delete.html'
    success_url = reverse_lazy('members:index')
    permission_required = ('members.delete_member')