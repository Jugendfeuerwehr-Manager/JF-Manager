"""Regression tests for account takeover and permission escalation routes."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient, APITestCase

from users.tokens import password_reset_token

User = get_user_model()


@override_settings(
    ALLOWED_HOSTS=["testserver"], CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class UserSecurityTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="leader", email="leader@example.com", password="Old-safe-river-42!"
        )
        self.victim = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="Other-safe-river-42!"
        )
        self.staff = User.objects.create_user(username="staff", password="Staff-safe-river-42!", is_staff=True)
        self.client.force_authenticate(self.user)

    def test_cannot_overwrite_another_users_email(self):
        response = self.client.patch(f"/api/v1/users/{self.victim.pk}/", {"email": "attacker@example.com"})
        self.assertEqual(response.status_code, 403)
        self.victim.refresh_from_db()
        self.assertEqual(self.victim.email, "admin@example.com")

    def test_public_user_route_cannot_create_staff(self):
        response = self.client.post("/api/v1/users/", {"username": "evil", "is_staff": True})
        self.assertEqual(response.status_code, 405)
        self.assertFalse(User.objects.filter(username="evil").exists())

    def test_profile_cannot_change_security_flags(self):
        response = self.client.patch(
            "/api/v1/users/me/", {"first_name": "Updated", "is_staff": True, "is_superuser": True, "is_active": False}
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.first_name, "Updated")

    def test_staff_cannot_manage_privileges_or_take_over_admin(self):
        self.client.force_authenticate(self.staff)
        group = Group.objects.create(name="Privileged")
        for url, payload in [
            (f"/api/v1/admin/users/{self.staff.pk}/", {"is_superuser": True}),
            (f"/api/v1/admin/users/{self.victim.pk}/", {"password": "Attacker-safe-river-42!"}),
            (f"/api/v1/admin/users/{self.staff.pk}/set-groups/", {"group_ids": [group.pk]}),
            (f"/api/v1/admin/groups/{group.pk}/", {"name": "Changed"}),
        ]:
            self.assertEqual(self.client.patch(url, payload, format="json").status_code, 403, url)
        self.assertEqual(self.client.post("/api/v1/admin/department-roles/", {}, format="json").status_code, 403)

    def reset_payload(self, token):
        return {
            "uid": urlsafe_base64_encode(force_bytes(self.user.pk)),
            "token": token,
            "new_password": "Fresh-safe-mountain-83!",
            "new_password_confirm": "Fresh-safe-mountain-83!",
        }

    def test_reset_token_is_single_use_and_revokes_all_credentials(self):
        browser = APIClient()
        browser.force_login(self.user)
        self.user.refresh_from_db()
        token = password_reset_token.make_token(self.user)
        self.assertEqual(browser.get("/api/v1/users/me/").status_code, 200)
        self.client.force_authenticate(None)
        response = self.client.post("/api/v1/users/reset_password/", self.reset_payload(token))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.post("/api/v1/users/reset_password/", self.reset_payload(token)).status_code, 400)
        # Existing sessions are bound to the old password hash.
        self.assertEqual(browser.get("/api/v1/users/me/").status_code, 401)

    def test_reset_token_expires_when_email_changes(self):
        token = password_reset_token.make_token(self.user)
        self.user.email = "new@example.com"
        self.user.save()
        self.assertFalse(password_reset_token.check_token(self.user, token))

    def test_disabled_user_cannot_reset_password(self):
        token = password_reset_token.make_token(self.user)
        self.user.is_active = False
        self.user.save()
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post("/api/v1/users/reset_password/", self.reset_payload(token)).status_code, 400)

    def test_legacy_token_logins_are_removed(self):
        self.client.force_authenticate(None)
        for path in ("/api/v1/auth/login/", "/api/v1/auth/refresh/", "/api/v1/auth/verify/", "/api-token-auth/"):
            response = self.client.post(path, {"username": "leader", "password": "Old-safe-river-42!"})
            self.assertEqual(response.status_code, 404, path)

    def test_bearer_and_token_headers_are_ignored(self):
        client = APIClient()
        for header in ("Bearer forged.jwt.value", "Token 0123456789abcdef"):
            client.credentials(HTTP_AUTHORIZATION=header)
            response = client.get("/api/v1/users/me/")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response["WWW-Authenticate"], 'Session realm="api"')

    def test_duplicate_email_reset_request_is_generic(self):
        User.objects.create_user(username="duplicate", email=self.user.email)
        response = self.client.post("/api/v1/users/request_password_reset/", {"email": self.user.email})
        self.assertEqual(response.status_code, 200)

    def test_login_attempts_are_limited(self):
        self.client.force_authenticate(None)
        url = "/api/v1/auth/session/login/"
        for _ in range(10):
            self.assertEqual(self.client.post(url, {"username": "missing", "password": "wrong"}).status_code, 401)
        self.assertEqual(self.client.post(url, {"username": "missing", "password": "wrong"}).status_code, 429)

    def test_oidc_unverified_email_cannot_claim_account(self):
        from django.core.exceptions import PermissionDenied

        from users.oidc_backend import JFManagerOIDCBackend

        backend = object.__new__(JFManagerOIDCBackend)
        backend.UserModel = User
        with self.assertRaises(PermissionDenied):
            backend.filter_users_by_claims(
                {"iss": "https://idp.example", "sub": "x", "email": self.victim.email, "email_verified": False}
            )
        with self.assertRaises(PermissionDenied):
            backend.filter_users_by_claims(
                {"iss": "https://idp.example", "sub": "x", "email": self.victim.email, "email_verified": True}
            )
        self.assertFalse(
            backend.filter_users_by_claims(
                {
                    "iss": "https://idp.example",
                    "sub": self.victim.username,
                    "email": "other@example.com",
                    "email_verified": True,
                }
            ).exists()
        )

    def test_oidc_identity_is_bound_even_after_email_change(self):
        from django.core.exceptions import PermissionDenied

        from users.oidc_backend import JFManagerOIDCBackend

        backend = object.__new__(JFManagerOIDCBackend)
        backend.UserModel = User
        self.user.auth_source = "oidc"
        self.user.oidc_issuer = "https://idp.example"
        self.user.oidc_subject = "original-subject"
        self.user.save()
        self.assertEqual(
            backend.filter_users_by_claims(
                {"iss": "https://idp.example", "sub": "original-subject", "email": "changed@example.com"}
            ).get(),
            self.user,
        )
        with self.assertRaises(PermissionDenied):
            backend.filter_users_by_claims(
                {
                    "iss": "https://idp.example",
                    "sub": "different-subject",
                    "email": self.user.email,
                    "email_verified": True,
                }
            )

    def test_legacy_oidc_account_requires_explicit_binding(self):
        from django.core.exceptions import PermissionDenied
        from django.core.management import call_command

        from users.oidc_backend import JFManagerOIDCBackend

        backend = object.__new__(JFManagerOIDCBackend)
        backend.UserModel = User
        self.user.auth_source = "oidc"
        self.user.save()
        claims = {
            "iss": "https://idp.example",
            "sub": "stable-subject",
            "email": self.user.email,
            "email_verified": True,
        }
        with self.assertRaises(PermissionDenied):
            backend.filter_users_by_claims(claims)
        call_command("bind_oidc_identity", self.user.username, claims["iss"], claims["sub"])
        self.assertEqual(backend.filter_users_by_claims(claims).get(), self.user)

    def test_new_oidc_user_persists_provider_identity(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        from users.oidc_backend import JFManagerOIDCBackend

        backend = object.__new__(JFManagerOIDCBackend)
        backend.UserModel = User
        config = SimpleNamespace(
            groups_claim="groups",
            require_group_mapping=False,
            staff_group="",
            admin_group="",
            provider_name="Test provider",
        )
        claims = {
            "iss": "https://idp.example",
            "sub": "new-stable-subject",
            "email": "new-oidc@example.com",
            "email_verified": True,
        }
        with patch.object(backend, "_get_config", return_value=config), patch.object(backend, "_sync_group_mappings"):
            user = backend.create_user(claims)
        user.refresh_from_db()
        self.assertEqual(user.auth_source, "oidc")
        self.assertEqual(user.oidc_issuer, claims["iss"])
        self.assertEqual(user.oidc_subject, claims["sub"])
        self.assertFalse(user.has_usable_password())
