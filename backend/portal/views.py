from datetime import timedelta

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
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
from .lifecycle import LifecycleError, access_state, access_states, child_access, end, extend, link_for, resume, suspend
from .people import portal_children, portal_self
from .permissions import PortalAccountRequired, StaffAccountRequired
from .serializers import (
    BulkInviteSerializer,
    ExtensionSerializer,
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    RecordRefSerializer,
)


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


ACCESS_STATES = {"none", "invited", "expired", "active", "suspended"}


class PortalAdminMixin:
    """Staff endpoints of the portal administration; scope = invite right per department."""

    permission_classes = [StaffAccountRequired, IsAuthenticated]

    def _record(self, data):
        refs = RecordRefSerializer(data=data)
        refs.is_valid(raise_exception=True)
        model, pk = (
            (Parent, refs.validated_data["parent"])
            if refs.validated_data.get("parent")
            else (
                Member,
                refs.validated_data["member"],
            )
        )
        record = get_object_or_404(scoped_records(self.request.user, model), pk=pk)
        if not may_invite(self.request.user, record):
            raise NotFound()
        return record

    @staticmethod
    def _fail(error):
        return Response({"detail": error.detail, "code": error.code}, status=error.status)


def _access_payload(record):
    link = link_for(record)
    account = None
    if link is not None and link.user.is_portal_account:
        account = {
            "username": link.user.username,
            "is_active": link.user.is_active,
            "last_login": link.user.last_login,
            "linked_at": link.linked_at,
        }
    kind = "parent" if isinstance(record, Parent) else "member"
    invitations = InvitationSerializer(record.portal_invitations.all()[:10], many=True).data
    return {
        "kind": kind,
        "id": record.pk,
        "name": record.get_full_name(),
        "email": record.email,
        "state": access_state(record),
        "account": account,
        "invitations": invitations,
        "children": child_access(record) if kind == "parent" else [],
    }


class PortalAccessView(PortalAdminMixin, APIView):
    """GET /portal/access/?parent=|member= — access, invitations and child access ends of one record."""

    def get(self, request):
        return Response(_access_payload(self._record(request.query_params)))


class PortalAccessActionView(PortalAdminMixin, APIView):
    """POST /portal/access/<suspend|resume|end>/ with {parent|member}."""

    actions = {"suspend": suspend, "resume": resume, "end": end}

    @extend_schema(request=RecordRefSerializer)
    def post(self, request, action_name):
        record = self._record(request.data)
        try:
            self.actions[action_name](record, request.user)
        except LifecycleError as error:
            return self._fail(error)
        return Response(_access_payload(record))


class PortalAccessExtensionView(PortalAdminMixin, APIView):
    """POST /portal/access/extensions/ — extend parent access beyond the 18th birthday."""

    @extend_schema(request=ExtensionSerializer)
    def post(self, request):
        data = ExtensionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        parent = self._record({"parent": data.validated_data["parent"]})
        member = get_object_or_404(parent.children.all(), pk=data.validated_data["member"])
        try:
            extend(parent, member, data.validated_data["until"], data.validated_data["reason"], request.user)
        except LifecycleError as error:
            return self._fail(error)
        return Response(_access_payload(parent), status=status.HTTP_201_CREATED)


class PortalAccessRecordsView(PortalAdminMixin, ListAPIView):
    """GET /portal/access/records/?kind=parent|member&state=&search= — overview for the admin area."""

    def get_queryset(self):
        model = Member if self.request.query_params.get("kind") == "member" else Parent
        records = scoped_records(self.request.user, model).order_by("lastname", "name", "pk")
        if model is Parent:
            records = records.prefetch_related("children")
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            records = records.filter(
                Q(name__icontains=search) | Q(lastname__icontains=search) | Q(email__icontains=search)
            )
        return records

    def list(self, request, *args, **kwargs):
        records = list(self.get_queryset()[:2000])
        states = access_states(records)
        wanted = request.query_params.get("state")
        if wanted in ACCESS_STATES:
            records = [r for r in records if states[r.pk] == wanted]
        page = self.paginate_queryset(records)
        rows = [
            {
                "kind": "parent" if isinstance(r, Parent) else "member",
                "id": r.pk,
                "name": r.get_full_name(),
                "email": r.email,
                "state": states[r.pk],
                "children": [c.get_full_name() for c in r.children.all()] if isinstance(r, Parent) else [],
            }
            for r in page
        ]
        return self.get_paginated_response(rows)


class PortalAccessEndingView(PortalAdminMixin, APIView):
    """GET /portal/access/ending/ — children whose parent access ends within 30 days or ended recently."""

    def get(self, request):
        today = timezone.localdate()
        parents = scoped_records(request.user, Parent).filter(account_link__isnull=False).prefetch_related("children")
        rows = []
        for parent in parents:
            for child in child_access(parent, today):
                if child["ends_soon"] or (child["ended"] and child["access_ends_on"] >= today - timedelta(days=90)):
                    rows.append({"parent": parent.pk, "parent_name": parent.get_full_name(), **child})
        rows.sort(key=lambda row: row["access_ends_on"])
        return Response(rows)


class BulkInviteView(PortalAdminMixin, APIView):
    """POST /portal/invitations/bulk/ {parents: [...]} — one result per parent, never all-or-nothing."""

    @extend_schema(request=BulkInviteSerializer)
    def post(self, request):
        data = BulkInviteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        results = []
        for pk in dict.fromkeys(data.validated_data["parents"]):
            try:
                record = self._record({"parent": pk})
                invite(record, request.user)
                results.append({"parent": pk, "result": "sent"})
            except (NotFound, Http404):
                results.append({"parent": pk, "result": "skipped", "code": "not_found"})
            except InvitationError as error:
                results.append({"parent": pk, "result": "skipped", "code": error.code, "detail": error.detail})
        return Response({"results": results})
