from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView
from inventory.models import Stock, Category, StorageLocation


class StockListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Stock
    template_name = 'inventory/stock_list.html'
    context_object_name = 'stocks'
    permission_required = 'inventory.view_stock'
    paginate_by = 50

    def get_queryset(self):  # pragma: no cover
        from django.db.models import Case, When, Value, CharField, F
        qs = Stock.objects.select_related(
            'item', 'item_variant', 'item_variant__parent_item', 'location'
        ).filter(quantity__gt=0)
        qs = qs.annotate(
            sort_name=Case(
                When(item__name__isnull=False, then=F('item__name')),
                When(item_variant__parent_item__name__isnull=False, then=F('item_variant__parent_item__name')),
                default=Value(''),
                output_field=CharField()
            )
        ).order_by('sort_name', 'location__name')
        return qs

    def get_context_data(self, **kwargs):  # pragma: no cover
        context = super().get_context_data(**kwargs)
        context['filter_categories'] = Category.objects.order_by('name')
        context['filter_locations'] = StorageLocation.objects.order_by('name')
        return context
