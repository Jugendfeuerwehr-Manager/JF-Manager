"""PORTAL-01.2: portal accounts reach nothing outside the allowlist."""

import re
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver, resolve
from django.urls.exceptions import Resolver404
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from departments.models import Department, RoleGrant, UserDepartmentRole
from members.models import Member
from portal.access import FORBIDDEN_CODE, PORTAL_ALLOWED_VIEW_NAMES, portal_route_allowed
from portal.permissions import PortalAccountRequired
from portal.signals import PortalAccountRoleDenied

User = get_user_model()

ROUTE_VALUES = {"int": "1", "str": "x", "slug": "x", "path": "x", "uuid": str(uuid.UUID(int=1))}


def _regex_group_value(match):
    body = match.group("body")
    if re.fullmatch(r"[\w|-]+", body) and "|" in body:
        return body.split("|")[0]  # alternatives such as admin app labels
    return "1"


def _concrete_path(pattern):
    """Turn a joined route/regex pattern into one request path that resolves to it."""
    path = re.sub(r"\(\?P<\w+>(?P<body>[^()]*)\)\??", _regex_group_value, pattern)
    path = re.sub(r"<(?:(\w+):)?\w+>", lambda m: ROUTE_VALUES.get(m.group(1) or "str", "x"), path)
    path = path.replace("^", "").replace("$", "").replace("\\.", ".").replace("/?", "/")
    return "/" + path


def _routes(patterns=None, prefix=""):
    """All URL patterns except format-suffix variants, which share the view of their base route."""
    for entry in get_resolver().url_patterns if patterns is None else patterns:
        if isinstance(entry, URLResolver):
            yield from _routes(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            pattern = prefix + str(entry.pattern)
            if "(?P<format>" not in pattern and "drf_format_suffix" not in pattern:
                yield pattern, entry


class PortalRouteAuditTests(TestCase):
    """Every registered route answers 403 for a portal account unless allowlisted."""

    @classmethod
    def setUpTestData(cls):
        cls.portal = User.objects.create_user("eltern", password="x", account_kind=User.AccountKind.PORTAL)

    def setUp(self):
        self.client.force_login(self.portal)  # a real session: the middleware sees it

    def test_every_route_outside_the_allowlist_is_forbidden(self):
        checked, unresolved, leaks = 0, [], []
        for pattern, _entry in _routes():
            path = _concrete_path(pattern)
            try:
                # A path shadowed by an earlier pattern is checked as that route.
                match = resolve(path)
            except Resolver404:
                unresolved.append(pattern)
                continue
            if portal_route_allowed(match):
                continue  # allowlisted, or a portal endpoint (see test_portal_endpoints_require_portal_accounts)
            for method in ("get", "post"):
                response = getattr(self.client, method)(path)
                checked += 1
                if response.status_code != 403:
                    leaks.append(f"{method.upper()} {path} -> {response.status_code}")
                elif path.startswith("/api/") and response.json().get("code") != FORBIDDEN_CODE:
                    leaks.append(f"{method.upper()} {path} -> 403 without portal code")
        self.assertEqual(unresolved, [], "Routen ohne prüfbaren Beispielpfad; _concrete_path erweitern")
        self.assertEqual(leaks, [])
        self.assertGreater(checked, 400)

    def test_allowlisted_routes_stay_reachable(self):
        self.assertEqual(self.client.get("/api/v1/auth/session/").status_code, 200)
        response = self.client.get("/api/v1/users/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "eltern")
        self.assertEqual(self.client.get("/api/v1/app/branding/").status_code, 200)

    def test_staff_routes_named_in_the_concept_are_closed(self):
        for path in [
            "/api/v1/users/",
            "/api/v1/settings/",
            "/api/v1/dashboard/summary/",
            "/admin/",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_staff_accounts_are_unaffected(self):
        staff = User.objects.create_user("betreuer", password="x")
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/api/v1/users/").status_code, 200)


class PortalAllowlistTests(TestCase):
    def test_allowlist_is_deliberate(self):
        # Widening the portal boundary must be a conscious, reviewed change.
        self.assertEqual(
            PORTAL_ALLOWED_VIEW_NAMES,
            {
                "session-status",
                "session-login",
                "session-logout",
                "session-mfa",
                "session-passkey",
                "session-passkey-options",
                "session-mfa-passkey-options",
                "reauthenticate",
                "reauth-passkey-options",
                "devices",
                "devices-revoke-others",
                "device-revoke",
                "mfa-status",
                "mfa-setup",
                "mfa-confirm",
                "mfa-recovery-codes",
                "mfa-disable",
                "mfa-totp-remove",
                "passkey-register-begin",
                "passkey-register-finish",
                "passkey-remove",
                "customuser-me",
                "customuser-change-password",
                "customuser-request-password-reset",
                "customuser-reset-password",
                "public-branding",
                "oidc-public-config",
                "csp-report",
                "health_check",
                "notification-preferences",
                "push-config",
                "push-subscription",
                "push-test",
                "action-resolve",
                "action-execute",
            },
        )

    def test_every_allowlisted_name_exists(self):
        names = {resolve(_concrete_path(pattern)).view_name for pattern, _ in _routes()}
        self.assertEqual(PORTAL_ALLOWED_VIEW_NAMES - names, set())


class PortalEndpointTests(TestCase):
    def test_portal_endpoints_require_portal_accounts(self):
        # A view that opts into portal access must not be reachable by everyone.
        endpoints = []
        for pattern, entry in _routes():
            view = getattr(entry.callback, "cls", None) or getattr(entry.callback, "view_class", None)
            if getattr(view, "portal_access", False) is True:
                endpoints.append(pattern)
                self.assertIn(PortalAccountRequired, view.permission_classes, pattern)
        self.assertIn("api/v1/portal/me/", endpoints)


class DefaultPermissionView(APIView):
    """Uses the DRF default permission classes, like most endpoints."""

    queryset = Member.objects.all()

    def get(self, request):
        return Response({"ok": True})


class StaffAccountRequiredTests(TestCase):
    """The DRF default layer also refuses portal accounts when no session middleware ran."""

    def _get(self, user, view_cls=DefaultPermissionView):
        request = APIRequestFactory().get("/api/v1/x/")
        force_authenticate(request, user)  # bypasses Django's session middleware
        return view_cls.as_view()(request)

    def test_default_permission_refuses_portal_account_even_with_model_rights(self):
        portal = User.objects.create_user("eltern", password="x", account_kind=User.AccountKind.PORTAL)
        portal.has_perm = lambda *args, **kwargs: True
        self.assertEqual(self._get(portal).status_code, 403)
        staff = User.objects.create_user("betreuer", password="x")
        staff.has_perm = lambda *args, **kwargs: True
        self.assertEqual(self._get(staff).status_code, 200)

    def test_portal_endpoint_marker_passes_the_default_layer(self):
        class PortalView(DefaultPermissionView):
            portal_access = True

        portal = User.objects.create_user("eltern", password="x", account_kind=User.AccountKind.PORTAL)
        portal.has_perm = lambda *args, **kwargs: True
        self.assertEqual(self._get(portal, PortalView).status_code, 200)


class PortalRoleGuardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.portal = User.objects.create_user("eltern", password="x", account_kind=User.AccountKind.PORTAL)
        cls.group = Group.objects.create(name="Testrolle")
        cls.department = Department.objects.create(name="Jugend")

    def test_no_groups_from_either_side(self):
        with transaction.atomic(), self.assertRaises(PortalAccountRoleDenied):
            self.portal.groups.add(self.group)
        with transaction.atomic(), self.assertRaises(PortalAccountRoleDenied):
            self.group.user_set.add(self.portal)
        self.assertFalse(self.portal.groups.exists())

    def test_no_direct_permissions(self):
        with transaction.atomic(), self.assertRaises(PortalAccountRoleDenied):
            self.portal.user_permissions.add(Permission.objects.first())

    def test_no_department_roles_or_role_sources(self):
        with transaction.atomic(), self.assertRaises(PortalAccountRoleDenied):
            UserDepartmentRole.objects.create(user=self.portal, department=self.department)
        with transaction.atomic(), self.assertRaises(PortalAccountRoleDenied):
            RoleGrant.objects.create(user=self.portal, group=self.group, department=self.department, source="local")

    def test_staff_accounts_keep_working(self):
        staff = User.objects.create_user("betreuer", password="x")
        staff.groups.add(self.group)
        self.group.user_set.add(staff)
        UserDepartmentRole.objects.create(user=staff, department=self.department)
        self.assertTrue(staff.groups.filter(pk=self.group.pk).exists())

    def test_role_assignment_api_answers_403(self):
        admin = User.objects.create_superuser("admin", password="x")
        client = APIClient()
        client.force_authenticate(admin)
        response = client.patch(
            f"/api/v1/admin/users/{self.portal.pk}/set-groups/", {"group_ids": [self.group.pk]}, format="json"
        )
        self.assertIn(response.status_code, {400, 403})
        self.assertFalse(self.portal.groups.exists())
