from django.urls import path

from .staff_views import (
    AssignmentPublishView,
    AssignmentView,
    MemberRegistrationView,
    SessionConfigView,
    SessionRegistrationsView,
)
from .views import EligibilityPreviewView, EligibilityValidateView

urlpatterns = [
    path("eligibility/validate/", EligibilityValidateView.as_view(), name="participation-eligibility-validate"),
    path("eligibility/preview/", EligibilityPreviewView.as_view(), name="participation-eligibility-preview"),
    path("sessions/<int:session_id>/config/", SessionConfigView.as_view(), name="participation-session-config"),
    path(
        "sessions/<int:session_id>/registrations/",
        SessionRegistrationsView.as_view(),
        name="participation-session-registrations",
    ),
    path(
        "sessions/<int:session_id>/registrations/<int:member_id>/",
        MemberRegistrationView.as_view(),
        name="participation-member-registration",
    ),
    path("sessions/<int:session_id>/assignment/", AssignmentView.as_view(), name="participation-assignment"),
    path(
        "sessions/<int:session_id>/assignment/publish/",
        AssignmentPublishView.as_view(),
        name="participation-assignment-publish",
    ),
]
