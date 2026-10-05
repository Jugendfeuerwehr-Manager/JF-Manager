import json
from datetime import date
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import ExportAudit, Member
from users import mfa
from users.models import MFADevice

User = get_user_model()
PASSWORD = "Synthetic-Passw0rd!"
SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


class StepUpTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.now = mfa.time.time()
        for target in ("users.mfa.time.time", "users.session_views.time.time", "users.session_policy.time.time"):
            patcher = patch(target, side_effect=lambda: self.now)
            patcher.start()
            self.addCleanup(patcher.stop)

    def code(self):
        return mfa.totp_at(SECRET, mfa.current_step())

    def login(self, user, with_mfa=False):
        client = APIClient(enforce_csrf_checks=True)
        client.get("/api/v1/auth/session/")
        client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
        status = client.post(
            "/api/v1/auth/session/login/", {"username": user.username, "password": PASSWORD}, format="json"
        )
        if with_mfa:
            self.assertTrue(status.data["mfa_required"])
            status = client.post("/api/v1/auth/session/mfa/", {"code": self.code()}, format="json")
        self.assertTrue(status.data["authenticated"], status.data)
        client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
        return client

    def admin(self):
        user = User.objects.create_user(username="account-admin", password=PASSWORD, is_staff=True, is_superuser=True)
        group = Group.objects.create(name="Synthetic identity admins")
        group.permissions.add(
            *Permission.objects.filter(content_type__app_label="auth", codename__in=["view_group", "add_group"])
        )
        user.groups.add(group)
        MFADevice.objects.create(user=user, secret=SECRET, confirmed_at="2026-01-01T00:00:00Z")
        return user

    def test_fresh_login_allows_access_changes_for_five_minutes(self):
        client = self.login(self.admin(), with_mfa=True)
        self.assertEqual(client.post("/api/v1/admin/groups/", {"name": "Fresh"}, format="json").status_code, 201)

    def test_access_changes_need_step_up_after_five_minutes(self):
        client = self.login(self.admin(), with_mfa=True)
        self.now += 301
        self.assertEqual(client.get("/api/v1/admin/groups/").status_code, 200)
        denied = client.post("/api/v1/admin/groups/", {"name": "Later"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "reauthentication_required")
        self.assertFalse(Group.objects.filter(name="Later").exists())
        self.now += 30
        confirm = client.post(
            "/api/v1/auth/reauthenticate/", {"password": PASSWORD, "code": self.code()}, format="json"
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertEqual(client.post("/api/v1/admin/groups/", {"name": "Later"}, format="json").status_code, 201)

    def test_step_up_does_not_reveal_endpoints_to_unauthorized_users(self):
        user = User.objects.create_user(username="plain", password=PASSWORD)
        client = self.login(user)
        self.now += 301
        response = client.post("/api/v1/admin/groups/", {"name": "Nope"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(response.json().get("code"), "reauthentication_required")

    def test_security_settings_need_step_up(self):
        user = self.admin()
        user.user_permissions.add(
            Permission.objects.get(codename="change_oidc_settings"),
            Permission.objects.get(codename="view_oidc_settings"),
        )
        client = self.login(user, with_mfa=True)
        self.now += 301
        self.assertEqual(client.get("/api/v1/settings/oidc/").status_code, 200)
        response = client.patch("/api/v1/settings/oidc/", {"provider_name": "Changed"}, format="json")
        self.assertEqual(response.json()["code"], "reauthentication_required")

    def test_spreadsheet_export_needs_step_up_and_is_audited(self):
        department = Department.objects.create(name="A", code="step-up-a")
        user = User.objects.create_user(username="exporter", password=PASSWORD)
        group = Group.objects.create(name="Synthetic exporters")
        group.permissions.add(
            *Permission.objects.filter(content_type__app_label="members", codename__in=["view_member", "export_member"])
        )
        UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)
        Member.objects.create(name="Synthetic", lastname="Member", birthday=date(2012, 1, 1)).departments.add(
            department
        )
        client = self.login(user)
        self.now += 301
        url = "/api/v1/members/export-excel/?columns=name"
        denied = client.get(url)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(json.loads(denied.content)["code"], "reauthentication_required")
        self.assertEqual(ExportAudit.objects.get().status_code, 403)
        self.now += 30
        self.assertEqual(
            client.post("/api/v1/auth/reauthenticate/", {"password": PASSWORD}, format="json").status_code, 200
        )
        self.assertEqual(client.get(url).status_code, 200)
