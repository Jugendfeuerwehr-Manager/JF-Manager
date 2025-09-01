from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse

from inventory.forms.transaction_improved import ImprovedTransactionForm
from inventory.models import Transaction, StorageLocation, Item, ItemVariant


class TransactionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Transaction
    template_name = 'inventory/transaction_list.html'
    context_object_name = 'transactions'
    permission_required = 'inventory.view_transaction'
    paginate_by = 30

    def get_queryset(self):  # pragma: no cover
        from django.db import models as dj_models
        queryset = Transaction.objects.select_related(
            'item', 'item_variant', 'item_variant__parent_item', 'source', 'target', 'user'
        ).order_by('-date')
        if (not self.request.user.has_perm('inventory.change_transaction') and hasattr(self.request.user, 'member')):
            member_location = StorageLocation.objects.filter(member=self.request.user.member).first()
            if member_location:
                queryset = queryset.filter(
                    dj_models.Q(source=member_location) | dj_models.Q(target=member_location)
                )
        return queryset

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['can_add_transaction'] = self.request.user.has_perm('inventory.add_transaction')
        return context


class TransactionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Transaction
    form_class = ImprovedTransactionForm
    template_name = 'inventory/transaction_form.html'
    permission_required = 'inventory.add_transaction'

    def get_form_kwargs(self):  # pragma: no cover
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        location_id = self.request.GET.get('location')
        target_id = self.request.GET.get('target')
        item_id = self.request.GET.get('item')
        variant_id = self.request.GET.get('item_variant')
        member_id = self.request.GET.get('member')
        trans_type = self.request.GET.get('type')
        if location_id:
            StorageLocation.objects.filter(pk=location_id).first() and kwargs.setdefault('initial_location', StorageLocation.objects.get(pk=location_id))
        if target_id:
            StorageLocation.objects.filter(pk=target_id).first() and kwargs.setdefault('initial_target', StorageLocation.objects.get(pk=target_id))
        if item_id:
            Item.objects.filter(pk=item_id).first() and kwargs.setdefault('initial_item', Item.objects.get(pk=item_id))
        if variant_id:
            ItemVariant.objects.filter(pk=variant_id).first() and kwargs.setdefault('initial_variant', ItemVariant.objects.get(pk=variant_id))
        if member_id and not target_id:
            from members.models import Member
            member = Member.objects.filter(pk=member_id).first()
            if member and not getattr(member, 'storage_location', None):
                member.storage_location = StorageLocation.objects.create(name=f"{member.name} {member.lastname}", is_member=True)
                member.save()
            if member and getattr(member, 'storage_location', None):
                kwargs.setdefault('initial_target', member.storage_location)
        if trans_type:
            kwargs['initial_transaction_type'] = trans_type
        return kwargs

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        for param, ctx_key in [('location', 'initial_location'), ('target', 'initial_target'), ('item', 'initial_item'), ('item_variant', 'initial_variant')]:
            value = self.request.GET.get(param)
            if value:
                model = {'location': StorageLocation, 'target': StorageLocation, 'item': Item, 'item_variant': ItemVariant}[param]
                obj = model.objects.filter(pk=value).first()
                if obj:
                    context[ctx_key] = obj
        member_id = self.request.GET.get('member')
        if member_id:
            context['member_id'] = member_id
        trans_type = self.request.GET.get('type')
        if trans_type:
            context['initial_transaction_type'] = trans_type
        return context

    def get_success_url(self):  # pragma: no cover
        return reverse('inventory:transaction_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):  # pragma: no cover
        form.instance.user = self.request.user
        transaction_type_dict = dict(Transaction.TRANSACTION_TYPES)
        type_name = transaction_type_dict.get(form.instance.transaction_type, 'Transaktion')
        messages.success(self.request, f'{type_name} für "{form.instance.get_item_name()}" wurde erfolgreich erstellt.')
        return super().form_valid(form)


class TransactionDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Transaction
    template_name = 'inventory/transaction_detail.html'
    permission_required = 'inventory.view_transaction'


class ImprovedTransactionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Transaction
    form_class = ImprovedTransactionForm
    template_name = 'inventory/transaction_form.html'
    permission_required = 'inventory.add_transaction'
    success_url = None  # Use get_success_url

    def get_success_url(self):  # pragma: no cover
        return reverse('inventory:transaction_list')

    def get_form_kwargs(self):  # pragma: no cover
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        mapping = {'source': 'initial_location', 'target': 'initial_target', 'item': 'initial_item', 'item_variant': 'initial_variant', 'type': 'initial_transaction_type', 'member': 'initial_member'}
        for param, key in mapping.items():
            val = self.request.GET.get(param)
            if not val:
                continue
            if param in ('source', 'target'):
                model = StorageLocation
            elif param == 'item':
                model = Item
            elif param == 'item_variant':
                model = ItemVariant
            elif param == 'member':
                from members.models import Member
                model = Member
            else:
                kwargs[key] = val
                continue
            obj = model.objects.filter(pk=val).first()
            if obj:
                kwargs[key] = obj
        return kwargs

    def form_valid(self, form):  # pragma: no cover
        transaction = form.save(commit=False)
        transaction.created_by = self.request.user
        transaction.save()
        transaction.process()
        item_name = transaction.item.name if transaction.item else str(transaction.item_variant)
        messages.success(self.request, f'Transaktion "{transaction.get_transaction_type_display()}" für "{item_name}" wurde erfolgreich ausgeführt.')
        return super().form_valid(form)

    def form_invalid(self, form):  # pragma: no cover
        messages.error(self.request, 'Es gab Fehler beim Erstellen der Transaktion. Bitte überprüfen Sie Ihre Eingaben.')
        return super().form_invalid(form)
