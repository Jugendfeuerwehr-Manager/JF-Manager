"""Mounted at ``api/v1/portal/sessions/`` (before the generic portal include)."""

from django.urls import path

from .portal_views import SessionListView, SessionRegistrationView

urlpatterns = [
    path("", SessionListView.as_view(), name="portal-sessions"),
    path(
        "<int:session_id>/registrations/<int:member_id>/",
        SessionRegistrationView.as_view(),
        name="portal-session-registration",
    ),
]
