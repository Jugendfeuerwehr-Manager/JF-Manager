from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from inventory.models import Item, Category, StorageLocation, Stock, Transaction
from django.db import models as dj_models


class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard.html'

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.has_perm('inventory.view_item'):
            context['total_items'] = Item.objects.count()
            context['total_categories'] = Category.objects.count()
        if user.has_perm('inventory.view_stock'):
            context['total_locations'] = StorageLocation.objects.count()
            context['total_stock_value'] = Stock.objects.aggregate(total=dj_models.Sum('quantity'))['total'] or 0
        if user.has_perm('inventory.view_transaction'):
            context['recent_transactions'] = Transaction.objects.select_related(
                'item', 'item_variant', 'item_variant__parent_item', 'source', 'target', 'user'
            ).order_by('-date')[:5]
        if hasattr(user, 'member'):
            member_location = StorageLocation.objects.filter(member=user.member).first()
            if member_location:
                context['my_loans'] = Stock.objects.filter(
                    location=member_location, quantity__gt=0
                ).select_related('item', 'item_variant', 'item_variant__parent_item')[:5]
        return context
