from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from members.models import Parent


class ParentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Parent
    template_name = 'parent_confirm_delete.html'
    success_url = reverse_lazy('members:parents')
    permission_required = 'members.delete_parent'