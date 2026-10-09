"""Mounted at ``api/v1/portal/absences/``."""

from django.urls import path

from .portal_views import AbsencePreviewView, AbsenceView

urlpatterns = [
    path("preview/", AbsencePreviewView.as_view(), name="portal-absence-preview"),
    path("", AbsenceView.as_view(), name="portal-absences"),
]
