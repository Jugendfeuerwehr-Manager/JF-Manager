from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import UpdateView

from members.forms import ParentForm
from members.models import Parent


class ParentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Parent
    form_class = ParentForm
    template_name = 'parent_edit.html'
    permission_required = 'members.change_parent'

    def get_success_url(self):
        return 'members:parents'

    def form_valid(self, form):
        item = form.save()
        item.save()
        return redirect('members:parents')