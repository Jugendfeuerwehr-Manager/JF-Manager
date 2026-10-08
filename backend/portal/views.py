from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from members.models import Member, Parent
from users.auth_security import PasswordActionThrottle
from users.session_views import SessionCsrfMixin

from .invitations import (
    InvitationError,
    accept,
    invite,
    may_invite,
    open_invitation,
    resend,
    revoke,
    scoped_invitations,
    scoped_records,
)
from .people import portal_children, portal_self
from .permissions import PortalAccountRequired, StaffAccountRequired
from .serializers import InvitationAcceptSerializer, InvitationCreateSerializer, InvitationSerializer


def _person(member, relation):
    # Names are always visible to the linked account (concept 4.2); further categories follow in PORTAL-02.
    return {"id": member.pk, "relation": relation, "first_name": member.name, "last_name": member.lastname}


class PortalMeView(APIView):
    """GET /api/v1/portal/me/ — the account and the people it may act for."""

    portal_access = True
    permission_classes = [PortalAccountRequired]

    @extend_schema(summary="Portal account and linked people")
    def get(self, request):
        user = request.user
        people = []
        member = portal_self(user)
        if member is not None:
            people.append(_person(member, "self"))
        people += [_person(child, "child") for child in portal_children(user)]
        return Response(
            {
                "account": {"first_name": user.first_name, "last_name": user.last_name, "email": user.email},
                "people": people,
            }
        )


class InvitationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Staff: list, send, resend and revoke portal invitations (PORTAL-01.3)."""

    permission_classes = [StaffAccountRequired, IsAuthenticated]
    serializer_class = InvitationSerializer

    def get_queryset(self):
        invitations = scoped_invitations(self.request.user)
        for field in ("parent", "member"):
            value = self.request.query_params.get(field)
            if value and value.isdigit():
                invitations = invitations.filter(**{field: int(value)})
        return invitations

    def _fail(self, error):
        return Response({"detail": error.detail, "code": error.code}, status=error.status)

    @extend_schema(request=InvitationCreateSerializer, responses={201: InvitationSerializer})
    def create(self, request):
        data = InvitationCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        model, pk = (
            (Parent, data.validated_data["parent"])
            if data.validated_data.get("parent")
            else (
                Member,
                data.validated_data["member"],
            )
        )
        # Records outside the inviting scope look like missing ones.
        record = get_object_or_404(scoped_records(request.user, model), pk=pk)
        if not may_invite(request.user, record):
            raise NotFound()
        try:
            invitation = invite(record, request.user)
        except InvitationError as error:
            return self._fail(error)
        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={200: InvitationSerializer})
    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        try:
            invitation = resend(self.get_object(), request.user)
        except InvitationError as error:
            return self._fail(error)
        return Response(InvitationSerializer(invitation).data)

    @extend_schema(request=None, responses={200: InvitationSerializer})
    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        try:
            invitation = revoke(self.get_object(), request.user)
        except InvitationError as error:
            return self._fail(error)
        return Response(InvitationSerializer(invitation).data)


class InvitationAcceptView(SessionCsrfMixin, APIView):
    """Public: GET ?token= shows whom an invitation is for, POST sets the password."""

    throttle_classes = [PasswordActionThrottle]

    def get(self, request):
        try:
            invitation = open_invitation(request.query_params.get("token", ""))
        except InvitationError as error:
            return Response({"detail": error.detail, "code": error.code}, status=error.status)
        return Response({"email": invitation.email, "kind": invitation.kind, "expires_at": invitation.expires_at})

    @extend_schema(request=InvitationAcceptSerializer)
    def post(self, request):
        data = InvitationAcceptSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            user = accept(data.validated_data["token"], data.validated_data["password"])
        except InvitationError as error:
            field = "password" if error.code == "password" else "detail"
            return Response({field: error.detail, "code": error.code}, status=error.status)
        return Response({"username": user.username}, status=status.HTTP_201_CREATED)
