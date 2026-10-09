from django.urls import path

from .inbox_views import InboxBulkReadView, InboxCountsView, InboxDoneView, InboxReadView, InboxView
from .preference_views import PreferenceView

urlpatterns = [
    path("inbox/", InboxView.as_view(), name="inbox"),
    path("preferences/", PreferenceView.as_view(), name="notification-preferences"),
    path("inbox/counts/", InboxCountsView.as_view(), name="inbox-counts"),
    path("inbox/read-bulk/", InboxBulkReadView.as_view(), name="inbox-read-bulk"),
    path("inbox/<int:item_id>/read/", InboxReadView.as_view(), name="inbox-read"),
    path("inbox/<int:item_id>/done/", InboxDoneView.as_view(), name="inbox-done"),
]
