from django.urls import path

from .inbox_views import InboxBulkReadView, InboxCountsView, InboxDoneView, InboxReadView, InboxView

urlpatterns = [
    path("inbox/", InboxView.as_view(), name="inbox"),
    path("inbox/counts/", InboxCountsView.as_view(), name="inbox-counts"),
    path("inbox/read-bulk/", InboxBulkReadView.as_view(), name="inbox-read-bulk"),
    path("inbox/<int:item_id>/read/", InboxReadView.as_view(), name="inbox-read"),
    path("inbox/<int:item_id>/done/", InboxDoneView.as_view(), name="inbox-done"),
]
