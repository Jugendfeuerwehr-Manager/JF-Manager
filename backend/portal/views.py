from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from departments.models import Department
from members.models import Member, Parent
from participation.throttles import PortalWriteThrottle
from users.auth_security import PasswordActionThrottle
from users.session_views import SessionCsrfMixin

from .change_requests import ChangeRequestError
from .change_requests import payload as change_payload
from .change_requests import submit as submit_change
from .change_requests import withdraw as withdraw_change
from .disclosure import parent_contact, person_payload
from .invitations import (
    InvitationError,
    accept,
    departments_with_permission,
    invite,
    may_invite,
    open_invitation,
    resend,
    revoke,
    scoped_invitations,
    scoped_records,
    security_log,
)
from .lifecycle import LifecycleError, access_state, access_states, child_access, end, extend, link_for, resume, suspend
from .models import ChangeRequest, PortalPolicy
from .people import confirmed_link, portal_children, portal_self
from .permissions import PortalAccountRequired, StaffAccountRequired
from .policy import ALLOWED, AUDIENCES, HIDDEN, LOCKED, NEVER_VISIBLE, VISIBLE, PolicySet, age_on
from .policy import CATEGORIES as POLICY_CATEGORIES
from .policy import applies as policy_applies
from .policy import is_fixed as policy_fixed
from .serializers import (
    BulkInviteSerializer,
    ExtensionSerializer,
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    PolicyWriteSerializer,
    RecordRefSerializer,
)


def _person(member, relation, policies):
    # Names are always visible (concept 4.2); the age only where the birthday is released.
    person = {"id": member.pk, "relation": relation, "first_name": member.name, "last_name": member.lastname}
    audience = "members" if relation == "self" else "parents"
    departments = [d.pk for d in member.departments.all()]
    if member.birthday and policies.visible("birthday", audience, departments):
        person["age"] = age_on(member.birthday, timezone.localdate())
    return person


class PortalMeView(APIView):
    """GET /api/v1/portal/me/ — the account and the people it may act for."""

    portal_access = True
    permission_classes = [PortalAccountRequired]

    @extend_schema(summary="Portal account and linked people")
    def get(self, request):
        user = request.user
        policies = PolicySet.load()
        people = []
        member = portal_self(user)
        if member is not None:
            people.append(_person(member, "self", policies))
        people += [_person(child, "child", policies) for child in portal_children(user).prefetch_related("departments")]
        link = confirmed_link(user)
        return Response(
            {
                "account": {"first_name": user.first_name, "last_name": user.last_name, "email": user.email},
                "people": people,
                # The parent's own record (always visible contact data; changes go through requests, E2).
                "parent": parent_contact(link.parent) if link and link.parent_id else None,
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


POLICY_PERMISSION = "portal.change_portalpolicy"


def _policy_scope(user):
    """(org editable, department ids editable or None for all)."""
    departments = departments_with_permission(user, POLICY_PERMISSION)
    org_editable = user.is_superuser or (
        user.has_perm("departments.can_access_all_departments") and user.has_perm(POLICY_PERMISSION)
    )
    return org_editable, departments


def _matrix(policies, department_id=None):
    values, locked = {}, {}
    for key in POLICY_CATEGORIES:
        for audience in AUDIENCES:
            if not policy_applies(key, audience):
                continue
            value = (
                policies.org_value(key, audience)
                if department_id is None
                else policies.department_value(department_id, key, audience)
            )
            values.setdefault(key, {})[audience] = value
            locked.setdefault(key, {})[audience] = policies.locked(key, audience)
    return values, locked


def _member_portal_stats(policies, department):
    members = list(Member.objects.filter(departments=department).only("pk", "birthday"))
    mode, min_age = policies.member_mode(department.pk)
    eligible = sum(1 for m in members if policies.member_allowed(m, [department.pk]))
    missing = sum(1 for m in members if m.birthday is None) if mode == "min_age" else 0
    return {"mode": mode, "min_age": min_age, "eligible": eligible, "missing_birthday": missing}


def _policy_overview(user):
    org_editable, editable_departments = _policy_scope(user)
    visible_departments = departments_with_permission(user, "portal.view_portalpolicy")
    if editable_departments is not None and visible_departments is not None:
        visible_departments = visible_departments | editable_departments
    elif editable_departments is None:
        visible_departments = None
    if not org_editable and visible_departments == set():
        raise PermissionDenied("Keine Berechtigung für Portal-Freigaben.")
    policies = PolicySet.load()
    org_values, org_locked = _matrix(policies)
    departments = Department.objects.order_by("name")
    if visible_departments is not None:
        departments = departments.filter(pk__in=visible_departments)
    rows = []
    for department in departments:
        values, locked = _matrix(policies, department.pk)
        policy = policies.departments.get(department.pk)
        rows.append(
            {
                "id": department.pk,
                "name": department.name,
                "editable": editable_departments is None or department.pk in editable_departments,
                "version": policy.version if policy else 0,
                "member_portal_mode": policy.member_portal_mode if policy else "",
                "member_portal_min_age": policy.member_portal_min_age if policy else None,
                "overrides": policy.visibility if policy else {},
                "effective": values,
                "locked": locked,
                "member_portal": _member_portal_stats(policies, department),
            }
        )
    org = policies.org
    return {
        "categories": [
            {
                "key": key,
                "label": label,
                "hint": hint,
                "fixed": fixed,
                "audiences": [a for a in AUDIENCES if policy_applies(key, a)],
            }
            for key, (label, hint, _p, _m, fixed) in POLICY_CATEGORIES.items()
        ],
        "never_visible": NEVER_VISIBLE,
        "organization": {
            "editable": org_editable,
            "version": org.version if org else 0,
            "member_portal_mode": (org.member_portal_mode if org else "") or "off",
            "member_portal_min_age": org.member_portal_min_age if org else None,
            "effective": org_values,
            "ceiling": {
                key: {a: (LOCKED if org_locked[key][a] else ALLOWED) for a in org_locked[key]} for key in org_locked
            },
        },
        "departments": rows,
    }


class PortalPolicyView(PortalAdminMixin, APIView):
    """GET /portal/policies/ — release matrix for the organisation and the departments in scope."""

    def get(self, request):
        return Response(_policy_overview(request.user))


def _clean_matrix(raw, allowed_values, policies, department_id):
    """Validate a {category: {audience: value}} map; returns cleaned map or raises errors dict."""
    cleaned, errors = {}, {}
    for key, audiences in (raw or {}).items():
        if key not in POLICY_CATEGORIES or not isinstance(audiences, dict):
            errors[key] = "Unbekannte Kategorie."
            continue
        for audience, value in audiences.items():
            where = f"{key}.{audience}"
            if audience not in AUDIENCES or not policy_applies(key, audience):
                errors[where] = "Diese Kategorie gibt es für diese Zielgruppe nicht."
            elif policy_fixed(key):
                errors[where] = "Diese Kategorie ist immer sichtbar und nicht einstellbar."
            elif value == "":
                continue
            elif value not in allowed_values:
                errors[where] = "Ungültiger Wert."
            elif department_id is not None and value == VISIBLE and policies.locked(key, audience):
                errors[where] = "Von der Organisation gesperrt."
            else:
                cleaned.setdefault(key, {})[audience] = value
    if errors:
        raise ValidationError(errors)
    return cleaned


class PortalPolicyUpdateView(PortalAdminMixin, APIView):
    """PUT /portal/policies/org/ or /portal/policies/<department_id>/ with the read version (409 if stale)."""

    @extend_schema(request=PolicyWriteSerializer)
    @transaction.atomic
    def put(self, request, department_id=None):
        org_editable, editable_departments = _policy_scope(request.user)
        if department_id is None:
            if not org_editable:
                raise PermissionDenied("Nur organisationsweite Portalverwaltung kann Vorgaben ändern.")
            department = None
        else:
            department = get_object_or_404(Department, pk=department_id)
            if editable_departments is not None and department.pk not in editable_departments:
                raise PermissionDenied("Keine Berechtigung für diese Abteilung.")
        data = PolicyWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        policy, _ = PortalPolicy.objects.select_for_update().get_or_create(
            department=department, defaults={"version": 0}
        )
        if values["version"] != policy.version:
            return Response({"code": "stale", "detail": "Die Freigaben wurden inzwischen geändert."}, status=409)
        policies = PolicySet.load()
        if "visibility" in values:
            policy.visibility = _clean_matrix(values["visibility"], {VISIBLE, HIDDEN}, policies, department_id)
        if department is None and "ceiling" in values:
            policy.ceiling = _clean_matrix(values["ceiling"], {ALLOWED, LOCKED}, policies, None)
        if "member_portal_mode" in values:
            mode = values["member_portal_mode"]
            if department is None and mode == "":
                raise ValidationError({"member_portal_mode": "Die Organisation braucht einen Wert."})
            min_age = values.get("member_portal_min_age")
            if mode == "min_age" and min_age is None:
                raise ValidationError({"member_portal_min_age": "Bitte ein Mindestalter angeben."})
            policy.member_portal_mode = mode
            policy.member_portal_min_age = min_age if mode == "min_age" else None
        policy.updated_by = request.user
        policy.version += 1
        policy.save()
        security_log.info("portal policy changed", extra={"policy": policy.pk, "actor": request.user.pk})
        return Response(_policy_overview(request.user))


class PortalPersonView(APIView):
    """GET /portal/people/<member_id>/ — released data of the own member record or a visible child."""

    portal_access = True
    permission_classes = [PortalAccountRequired]

    def get(self, request, member_id):
        user = request.user
        own = portal_self(user)
        link = confirmed_link(user)
        if own is not None and own.pk == member_id:
            return Response(person_payload(own, "self"))
        child = portal_children(user).filter(pk=member_id).first()
        if child is None:
            raise NotFound()  # foreign ids look like missing ones (concept 5.2.3)
        return Response(person_payload(child, "child", viewer_parent=link.parent if link else None))


def _portal_targets(user):
    """Records the account may request changes for: own member record, visible children, own parent record."""
    link = confirmed_link(user)
    if link is None:
        return [], None
    members = list(portal_children(user)) if link.parent_id else []
    if link.member_id:
        members.insert(0, link.member)
    return members, link.parent


def _portal_target(user, data):
    members, parent = _portal_targets(user)
    kind = data.get("kind") if isinstance(data, dict) else None
    if kind == "parent" and parent is not None:
        return parent
    if kind == "member":
        match = [m for m in members if str(m.pk) == str(data.get("id"))]
        if match:
            return match[0]
    raise NotFound()  # foreign ids look like missing ones (concept 5.2.3)


def _cr_fail(error):
    return Response({"detail": error.detail, "code": error.code, "fields": error.fields}, status=error.status)


class PortalChangeRequestsView(APIView):
    """GET/POST /portal/change-requests/ — own requests per person; submitting again updates the open one (E2)."""

    portal_access = True
    permission_classes = [PortalAccountRequired]
    throttle_classes = [PortalWriteThrottle]

    def get(self, request):
        members, parent = _portal_targets(request.user)
        query = Q(target_member__in=members)
        if parent is not None:
            query |= Q(target_parent=parent)
        recent = ChangeRequest.objects.filter(query).select_related("target_member", "target_parent")[:30]
        return Response({"results": [change_payload(r) for r in recent]})

    def post(self, request):
        record = _portal_target(request.user, request.data.get("target"))
        try:
            change, created = submit_change(record, request.data.get("fields"), request.user)
        except ChangeRequestError as error:
            return _cr_fail(error)
        security_log.info("change request submitted", extra={"change_request": change.pk, "actor": request.user.pk})
        return Response(change_payload(change, record), status=status.HTTP_201_CREATED if created else 200)


class PortalChangeRequestWithdrawView(APIView):
    """POST /portal/change-requests/<id>/withdraw/ — only for a person the account may act for."""

    portal_access = True
    permission_classes = [PortalAccountRequired]
    throttle_classes = [PortalWriteThrottle]

    def post(self, request, pk):
        members, parent = _portal_targets(request.user)
        query = Q(target_member__in=members)
        if parent is not None:
            query |= Q(target_parent=parent)
        change = ChangeRequest.objects.filter(query, pk=pk).first()
        if change is None:
            raise NotFound()
        try:
            change = withdraw_change(change)
        except ChangeRequestError as error:
            return _cr_fail(error)
        return Response(change_payload(change))
