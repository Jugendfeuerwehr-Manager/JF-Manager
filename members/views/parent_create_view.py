from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView

from inventory.forms import FormActionMixin
from members.forms import ParentForm
from members.models import Parent


class ParentCreateView(FormActionMixin, PermissionRequiredMixin, CreateView):
    model = Parent
    form_class = ParentForm
    template_name = 'parent_edit.html'
    permission_required = 'members.add_parent'

    def get_success_url(self):
        return 'members:parents'

    def form_valid(self, form):
        item = form.save()
        item.save()
        return redirect('members:parents')