from django.urls import include, path, re_path
from rest_framework.routers import SimpleRouter

from notifications.inbox_views import PortalNotificationReadView, PortalNotificationsView

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
    PortalPersonView,
    PortalPolicyUpdateView,
    PortalPolicyView,
)

router = SimpleRouter()
router.register("invitations", InvitationViewSet, basename="portal-invitations")

urlpatterns = [
    path("me/", PortalMeView.as_view(), name="portal-me"),
    path("notifications/", PortalNotificationsView.as_view(), name="portal-notifications"),
    path("notifications/<int:item_id>/read/", PortalNotificationReadView.as_view(), name="portal-notification-read"),
    path("people/<int:member_id>/", PortalPersonView.as_view(), name="portal-person"),
    path("policies/", PortalPolicyView.as_view(), name="portal-policies"),
    path("policies/org/", PortalPolicyUpdateView.as_view(), name="portal-policy-org"),
    path("policies/<int:department_id>/", PortalPolicyUpdateView.as_view(), name="portal-policy-department"),
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
