"""Mounted at ``api/v1/my/``: own area of linked staff accounts (PORTAL-04.3)."""

from django.urls import path

from .self_views import (
    OwnAbsencePreviewView,
    OwnAbsenceView,
    OwnOverviewView,
    OwnPersonView,
    OwnSessionListView,
    OwnSessionRegistrationView,
)

urlpatterns = [
    path("", OwnOverviewView.as_view(), name="own-overview"),
    path("people/<int:member_id>/", OwnPersonView.as_view(), name="own-person"),
    path("sessions/", OwnSessionListView.as_view(), name="own-sessions"),
    path(
        "sessions/<int:session_id>/registrations/<int:member_id>/",
        OwnSessionRegistrationView.as_view(),
        name="own-session-registration",
    ),
    path("absences/preview/", OwnAbsencePreviewView.as_view(), name="own-absence-preview"),
    path("absences/", OwnAbsenceView.as_view(), name="own-absences"),
]
