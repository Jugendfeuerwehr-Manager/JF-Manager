from django.urls import path

from .views import PortalMeView

urlpatterns = [
    path("me/", PortalMeView.as_view(), name="portal-me"),
]
