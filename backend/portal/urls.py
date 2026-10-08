from django.urls import include, path, re_path
from rest_framework.routers import SimpleRouter

from .views import (
    BulkInviteView,
    InvitationAcceptView,
    InvitationViewSet,
    PortalAccessActionView,
    PortalAccessEndingView,
    PortalAccessExtensionView,
    PortalAccessRecordsView,
    PortalAccessView,
    PortalMeView,
)

router = SimpleRouter()
router.register("invitations", InvitationViewSet, basename="portal-invitations")

urlpatterns = [
    path("me/", PortalMeView.as_view(), name="portal-me"),
    # Before the router: "accept" is not an invitation id.
    path("invitations/accept/", InvitationAcceptView.as_view(), name="portal-invitation-accept"),
    path("invitations/bulk/", BulkInviteView.as_view(), name="portal-invitation-bulk"),
    path("access/", PortalAccessView.as_view(), name="portal-access"),
    path("access/records/", PortalAccessRecordsView.as_view(), name="portal-access-records"),
    path("access/ending/", PortalAccessEndingView.as_view(), name="portal-access-ending"),
    path("access/extensions/", PortalAccessExtensionView.as_view(), name="portal-access-extension"),
    re_path(
        r"^access/(?P<action_name>suspend|resume|end)/$", PortalAccessActionView.as_view(), name="portal-access-action"
    ),
    path("", include(router.urls)),
]
