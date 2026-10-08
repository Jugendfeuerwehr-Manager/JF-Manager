from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import InvitationAcceptView, InvitationViewSet, PortalMeView

router = SimpleRouter()
router.register("invitations", InvitationViewSet, basename="portal-invitations")

urlpatterns = [
    path("me/", PortalMeView.as_view(), name="portal-me"),
    # Before the router: "accept" is not an invitation id.
    path("invitations/accept/", InvitationAcceptView.as_view(), name="portal-invitation-accept"),
    path("", include(router.urls)),
]
