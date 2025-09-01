from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView
from inventory.models import Transaction, StorageLocation
from django.db import models as dj_models


class MemberLoanListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Transaction
    template_name = 'inventory/member_loans.html'
    context_object_name = 'loans'

    def test_func(self):  # pragma: no cover
        return hasattr(self.request.user, 'member')

    def get_queryset(self):  # pragma: no cover
        if not hasattr(self.request.user, 'member'):
            return Transaction.objects.none()
        member_location = StorageLocation.objects.filter(member=self.request.user.member).first()
        if not member_location:
            return Transaction.objects.none()
        loans = Transaction.objects.filter(
            transaction_type='LOAN',
            target=member_location
        ).select_related('item', 'item_variant', 'item_variant__parent_item', 'source')
        returned_item_ids = Transaction.objects.filter(
            transaction_type='RETURN', source=member_location, item__isnull=False
        ).values_list('item_id', flat=True)
        returned_variant_ids = Transaction.objects.filter(
            transaction_type='RETURN', source=member_location, item_variant__isnull=False
        ).values_list('item_variant_id', flat=True)
        loans = loans.exclude(
            dj_models.Q(item_id__in=returned_item_ids) | dj_models.Q(item_variant_id__in=returned_variant_ids)
        )
        return loans
