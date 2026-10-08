from django.urls import path

from .views import EligibilityPreviewView, EligibilityValidateView

urlpatterns = [
    path("eligibility/validate/", EligibilityValidateView.as_view(), name="participation-eligibility-validate"),
    path("eligibility/preview/", EligibilityPreviewView.as_view(), name="participation-eligibility-preview"),
]
