"""API for staff account links (PORTAL-04, concept 5.3).

Account management (``users.change_customuser`` in a department of the record)
links, lists and releases; the linked account itself sees its pending link,
confirms or rejects it and may ask for release. Portal accounts never reach
these routes (PortalBoundaryMiddleware, StaffAccountRequired).
"""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from members.models import Member, Parent
from users.people import person_accounts

from . import account_links as links
from .models import AccountLink
from .permissions import StaffAccountRequired

User = get_user_model()


class LinkCreateSerializer(serializers.Serializer):
    user = serializers.IntegerField(min_value=1)
    member = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    parent = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    # Only system administration may convert a member's portal account into this link.
    transfer = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get("member") and not attrs.get("parent"):
            raise serializers.ValidationError("Bitte ein Mitglied oder einen Elterndatensatz wählen.")
        return attrs


def _fail(error):
    return Response({"detail": error.detail, "code": error.code}, status=error.status)


class AccountLinkViewSet(viewsets.GenericViewSet):
    """/api/v1/portal/account-links/ — link staff accounts to member and parent records."""

    permission_classes = [StaffAccountRequired, IsAuthenticated]
    queryset = AccountLink.objects.none()
    serializer_class = LinkCreateSerializer

    def _require_management(self):
        if not links.may_manage_links(self.request.user):
            raise PermissionDenied("Keine Berechtigung für die Kontoverwaltung.")

    def _record(self, model, pk):
        record = model.objects.filter(pk=pk).first()
        # Records outside the actor's scope look like missing ones.
        if record is None or not links.may_link(self.request.user, record):
            raise NotFound()
        return record

    def get_object(self):
        self._require_management()
        return get_object_or_404(links.scoped_links(self.request.user), pk=self.kwargs["pk"])

    @extend_schema(summary="Account links in scope, filtered by user, member or parent")
    def list(self, request):
        self._require_management()
        queryset = links.scoped_links(request.user)
        for field in ("user", "member", "parent"):
            value = request.query_params.get(field)
            if value is not None:
                if not value.isdigit():
                    return Response({"results": []})
                queryset = queryset.filter(**{field: int(value)})
        rows = [links.link_payload(link) for link in queryset.order_by("-linked_at")[:200]]
        return Response({"results": rows})

    @extend_schema(request=LinkCreateSerializer, summary="Link a staff account (pending until it confirms)")
    def create(self, request):
        self._require_management()
        data = LinkCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        member = self._record(Member, values["member"]) if values.get("member") else None
        parent = self._record(Parent, values["parent"]) if values.get("parent") else None
        user = person_accounts(active_only=False).filter(pk=values["user"]).first()
        if user is None:
            raise NotFound()
        try:
            link, changed = links.link(request.user, user, member=member, parent=parent, transfer=values["transfer"])
        except links.LinkError as error:
            return _fail(error)
        return Response(links.link_payload(link), status=status.HTTP_201_CREATED if changed else status.HTTP_200_OK)

    @extend_schema(summary="Release a link or one of its records (?target=member|parent)")
    def destroy(self, request, pk=None):
        link = self.get_object()
        target = request.query_params.get("target")
        if target is not None and target not in links.FIELDS:
            return Response({"detail": "Unbekanntes Ziel.", "code": "target"}, status=400)
        for field in [target] if target else links.FIELDS:
            record = getattr(link, field)
            if record is not None and not links.may_link(request.user, record):
                raise NotFound()
        try:
            remaining = links.unlink(request.user, link, target)
        except links.LinkError as error:
            return _fail(error)
        if remaining is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(links.link_payload(remaining))

    @extend_schema(summary="Records or accounts that probably belong together (same e-mail or name)")
    @action(detail=False, methods=["get"])
    def suggestions(self, request):
        self._require_management()
        params = request.query_params
        if (params.get("user") or "").isdigit():
            user = get_object_or_404(User.objects.filter(account_kind=User.AccountKind.STAFF), pk=int(params["user"]))
            return Response({"results": links.suggestions_for_user(request.user, user)})
        for field, model in (("member", Member), ("parent", Parent)):
            if (params.get(field) or "").isdigit():
                return Response({"results": links.suggestions_for_record(self._record(model, int(params[field])))})
        return Response({"results": []})

    @extend_schema(summary="Search staff accounts for the link dialog (?search=)")
    @action(detail=False, methods=["get"])
    def accounts(self, request):
        self._require_management()
        return Response({"results": links.search_accounts(request.query_params.get("search", ""))})

    # ------------------------------------------------------------- qualification duplicates (04.4)
    def _merge_target(self, member_id):
        from .invitations import departments_with_permission, record_department_ids
        from .qualification_merge import link_for_member, may_merge

        member = Member.objects.filter(pk=member_id).first() if isinstance(member_id, int) else None
        if member is None:
            raise NotFound()
        if not may_merge(self.request.user, member):
            # Without any qualification view right in the member's departments it looks missing.
            visible = departments_with_permission(self.request.user, "qualifications.view_qualification")
            if visible is not None and not (visible & record_department_ids(member)):
                raise NotFound()
            raise PermissionDenied("Keine Berechtigung, Qualifikationen dieses Mitglieds zusammenzuführen.")
        return member, link_for_member(member)

    @extend_schema(summary="Qualification types recorded at the linked account and the member (?member=)")
    @action(detail=False, methods=["get"])
    def duplicates(self, request):
        from .qualification_merge import duplicates

        value = request.query_params.get("member") or ""
        _member, link = self._merge_target(int(value) if value.isdigit() else None)
        return Response({"link": link.pk if link else None, "results": duplicates(link)})

    @extend_schema(summary="Merge account qualifications into the member (evidence stays at the member)")
    @action(detail=False, methods=["post"], url_path="merge-qualifications")
    def merge_qualifications(self, request):
        from .qualification_merge import MergeError, duplicates, merge

        _member, link = self._merge_target(request.data.get("member"))
        if link is None:
            return Response({"detail": "Kein bestätigtes Konto verknüpft.", "code": "not_linked"}, status=409)
        ids = request.data.get("qualifications")
        try:
            merged = merge(request.user, link, ids if isinstance(ids, list) else [])
        except MergeError as error:
            return _fail(error)
        return Response({"merged": merged, "results": duplicates(link)})

    # ------------------------------------------------------------- the linked account itself
    @extend_schema(summary="Own pending link for the login step (E13)")
    @action(detail=False, methods=["get"], url_path="pending-for-me")
    def pending_for_me(self, request):
        link = links.pending_for(request.user)
        return Response({"link": links.link_payload(link) if link else None})

    def _decide(self, request, pk, accept):
        try:
            link = links.decide(request.user, int(pk), accept)
        except (TypeError, ValueError):
            raise NotFound() from None
        except links.LinkError as error:
            return _fail(error)
        return Response(links.link_payload(link))

    @extend_schema(request=None, summary="Confirm the own pending link")
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._decide(request, pk, True)

    @extend_schema(request=None, summary="Reject the own pending link")
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decide(request, pk, False)

    @extend_schema(request=None, summary="Ask account management to release the own confirmed link")
    @action(detail=False, methods=["post"], url_path="release-request")
    def release_request(self, request):
        try:
            created = links.request_release(request.user)
        except links.LinkError as error:
            return _fail(error)
        return Response({"requested": True, "new": created})
