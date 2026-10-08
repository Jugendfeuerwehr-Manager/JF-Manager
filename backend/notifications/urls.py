from django.urls import path

from .views import PushConfigView, PushSubscriptionView, PushTestView

urlpatterns = [
    path("config/", PushConfigView.as_view(), name="push-config"),
    path("subscription/", PushSubscriptionView.as_view(), name="push-subscription"),
    path("test/", PushTestView.as_view(), name="push-test"),
]
