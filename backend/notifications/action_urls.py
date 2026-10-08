from django.urls import path

from .action_views import ExecuteView, ResolveView

urlpatterns = [
    path("resolve/", ResolveView.as_view(), name="action-resolve"),
    path("execute/", ExecuteView.as_view(), name="action-execute"),
]
