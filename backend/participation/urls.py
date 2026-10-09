from django.urls import path

from .staff_views import (
    AssignmentPublishView,
    AssignmentView,
    MemberRegistrationView,
    SessionConfigView,
    SessionRegistrationsView,
)
from .template_views import (
    ApplyTemplateView,
    TemplateArchiveView,
    TemplateDetailView,
    TemplateListView,
    TemplateUnarchiveView,
    TrainingTemplateParticipationView,
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
    path("sessions/<int:session_id>/apply-template/", ApplyTemplateView.as_view(), name="participation-apply-template"),
    path("templates/", TemplateListView.as_view(), name="participation-templates"),
    path("templates/<int:pk>/", TemplateDetailView.as_view(), name="participation-template"),
    path("templates/<int:pk>/archive/", TemplateArchiveView.as_view(), name="participation-template-archive"),
    path("templates/<int:pk>/unarchive/", TemplateUnarchiveView.as_view(), name="participation-template-unarchive"),
    path(
        "training-templates/<int:pk>/",
        TrainingTemplateParticipationView.as_view(),
        name="participation-training-template",
    ),
]
