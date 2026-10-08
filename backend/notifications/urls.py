from django.urls import path

from .views import PushConfigView, PushSubscriptionView, PushTestView

urlpatterns = [
    path("config/", PushConfigView.as_view()),
    path("subscription/", PushSubscriptionView.as_view()),
    path("test/", PushTestView.as_view()),
]
