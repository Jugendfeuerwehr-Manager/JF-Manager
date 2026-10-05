from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from departments.models import Department, RoleTemplate, UserDepartmentRole
from users import mfa
from users.mfa_policy import mfa_required
from users.models import MFADevice

User = get_user_model()
PASSWORD = "Synthetic-Passw0rd!"
SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/v1/auth/session/")
    client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
    return client


def refresh_csrf(client):
    client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)


class MFALoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="mfa-login", password=PASSWORD)
        MFADevice.objects.create(user=self.user, secret=SECRET, confirmed_at="2026-01-01T00:00:00Z")
        self.codes = mfa.issue_recovery_codes(self.user)
        self.now = mfa.time.time()
        for target in ("users.mfa.time.time", "users.session_views.time.time"):
            patcher = patch(target, side_effect=lambda: self.now)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = csrf_client()

    def password_step(self):
        before = (
            self.client.cookies[settings.SESSION_COOKIE_NAME].value
            if settings.SESSION_COOKIE_NAME in self.client.cookies
            else None
        )
        response = self.client.post(
            "/api/v1/auth/session/login/", {"username": "mfa-login", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"authenticated": False, "mfa_required": True})
        self.assertNotEqual(self.client.cookies[settings.SESSION_COOKIE_NAME].value, before)
        return response

    def code(self, offset=0):
        return mfa.totp_at(SECRET, mfa.current_step() + offset)

    def test_password_alone_does_not_authenticate(self):
        self.password_step()
        self.assertIn(self.client.get("/api/v1/users/me/").status_code, (401, 403))
        self.assertEqual(self.client.get("/api/v1/auth/session/").data, {"authenticated": False, "mfa_required": True})

    def test_totp_completes_login_and_rotates_csrf(self):
        self.password_step()
        old_csrf = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        response = self.client.post("/api/v1/auth/session/mfa/", {"code": self.code()}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["authenticated"])
        self.assertNotEqual(self.client.cookies[settings.CSRF_COOKIE_NAME].value, old_csrf)
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 200)

    def test_recovery_code_completes_login_once(self):
        self.password_step()
        self.assertEqual(
            self.client.post("/api/v1/auth/session/mfa/", {"code": self.codes[0]}, format="json").status_code, 200
        )
        refresh_csrf(self.client)
        self.client.post("/api/v1/auth/session/logout/")
        self.password_step()
        self.assertEqual(
            self.client.post("/api/v1/auth/session/mfa/", {"code": self.codes[0]}, format="json").status_code, 400
        )

    def test_code_step_requires_csrf(self):
        self.password_step()
        self.client.credentials()
        self.assertEqual(
            self.client.post("/api/v1/auth/session/mfa/", {"code": self.code()}, format="json").status_code, 403
        )

    def test_attempts_are_limited_per_pending_login(self):
        self.password_step()
        for _ in range(5):
            self.assertEqual(
                self.client.post("/api/v1/auth/session/mfa/", {"code": "000000"}, format="json").status_code, 400
            )
        response = self.client.post("/api/v1/auth/session/mfa/", {"code": self.code()}, format="json")
        self.assertEqual(response.data["code"], "mfa_login_expired")

    def test_pending_login_expires(self):
        self.password_step()
        self.now += 301
        response = self.client.post("/api/v1/auth/session/mfa/", {"code": self.code()}, format="json")
        self.assertEqual(response.data["code"], "mfa_login_expired")

    def test_session_created_without_second_factor_is_ended(self):
        client = APIClient()
        client.force_login(self.user)
        self.assertIn(client.get("/api/v1/users/me/").status_code, (401, 403))
        admin = client.get("/admin/")
        self.assertEqual(admin.status_code, 302)


@override_settings(FRONTEND_URL="https://jf.example.test")
class MFAPolicyTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_privileged_accounts_require_mfa(self):
        plain = User.objects.create_user(username="plain")
        staff = User.objects.create_user(username="staff", is_staff=True)
        admin_group = Group.objects.create(name="Synthetic account admins")
        admin_group.permissions.add(
            Permission.objects.get(content_type__app_label="users", codename="change_customuser")
        )
        global_admin = User.objects.create_user(username="global-admin")
        global_admin.groups.add(admin_group)
        department = Department.objects.create(name="A", code="mfa-a")
        leader_group = Group.objects.create(name="Synthetic leaders")
        RoleTemplate.objects.create(
            key="department_youth_director", group=leader_group, name="Leitung", scope="department"
        )
        leader = User.objects.create_user(username="leader")
        UserDepartmentRole.objects.create(user=leader, department=department).groups.add(leader_group)
        scoped_admin = User.objects.create_user(username="scoped-admin")
        UserDepartmentRole.objects.create(user=scoped_admin, department=department).groups.add(admin_group)
        self.assertFalse(mfa_required(plain))
        for user in (staff, global_admin, leader, scoped_admin):
            self.assertTrue(mfa_required(user), user.username)

    def test_required_account_can_only_enrol_until_mfa_is_active(self):
        User.objects.create_user(username="staff-login", password=PASSWORD, is_staff=True)
        client = csrf_client()
        response = client.post(
            "/api/v1/auth/session/login/", {"username": "staff-login", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.data["mfa_setup_required"], True)
        refresh_csrf(client)
        blocked = client.get("/api/v1/members/")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["code"], "mfa_setup_required")
        self.assertEqual(client.get("/admin/").status_code, 302)
        self.assertEqual(client.get("/api/v1/users/me/").status_code, 200)
        secret = client.post("/api/v1/auth/mfa/setup/").data["secret"]
        confirm = client.post(
            "/api/v1/auth/mfa/confirm/", {"code": mfa.totp_at(secret, mfa.current_step())}, format="json"
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertTrue(confirm.data["required"])
        self.assertNotEqual(client.get("/api/v1/members/").json().get("code"), "mfa_setup_required")
        self.assertEqual(client.get("/admin/").status_code, 200)
        self.assertEqual(client.post("/api/v1/auth/mfa/disable/").status_code, 409)

    def test_legacy_login_forms_redirect_to_central_login(self):
        for path in ("/admin/login/", "/accounts/login/", "/api-auth/login/"):
            response = self.client.get(path, {"next": "//evil.example/"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response["Location"], "https://jf.example.test/login?next=%2Fadmin%2F")
        self.assertEqual(self.client.post("/accounts/password_reset/", {"email": "x@example.test"}).status_code, 404)
