"""SEC-06.4: unreadable identity-provider secrets must not break local sign-in."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient, APITestCase

from settings_manager.models import LDAPConfig, OIDCConfig

User = get_user_model()
PASSWORD = "Synthetic-Passw0rd!"
# Valid Fernet layout, but encrypted with a key that is not in the key ring.
FOREIGN_CIPHER = "gAAAAABk" + "A" * 92


def corrupt(table, column):
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE {table} SET {column} = %s", [FOREIGN_CIPHER])


class AuthConfigResilienceTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="local-user", password=PASSWORD)

    def login(self):
        return APIClient().post("/api/v1/auth/session/login/", {"username": "local-user", "password": PASSWORD})

    def test_permission_checks_do_not_read_identity_provider_configuration(self):
        with (
            patch.object(OIDCConfig, "get_or_create_default", side_effect=AssertionError("OIDC config read")),
            patch.object(LDAPConfig.objects, "order_by", side_effect=AssertionError("LDAP config read")),
        ):
            self.assertFalse(self.user.has_perm("members.view_member"))

    def test_unreadable_ldap_secret_disables_ldap_but_not_local_login(self):
        LDAPConfig.objects.create(
            pk=1,
            enabled=True,
            server_uri="ldaps://ldap.example.test",
            user_search_base_dn="dc=example,dc=test",
            user_search_filter="(uid=%(user)s)",
            bind_dn="cn=reader,dc=example,dc=test",
            bind_password="synthetic",
        )
        corrupt("settings_manager_ldapconfig", "bind_password")
        with self.assertLogs("users.ldap_backend", level="ERROR"):
            response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["authenticated"])

    def test_disabled_ldap_secret_is_never_decrypted(self):
        LDAPConfig.objects.create(pk=1, enabled=False, bind_password="synthetic")
        corrupt("settings_manager_ldapconfig", "bind_password")
        self.assertEqual(self.login().status_code, 200)

    def test_unreadable_oidc_secret_keeps_login_page_and_local_login_working(self):
        config = OIDCConfig.get_or_create_default()
        config.client_secret = "synthetic"
        config.save()
        corrupt("settings_manager_oidcconfig", "client_secret")
        self.assertEqual(APIClient().get("/api/v1/auth/oidc/public-config/").status_code, 200)
        self.assertEqual(self.login().status_code, 200)

    def test_singleton_creation_tolerates_an_existing_row(self):
        first = OIDCConfig.get_or_create_default()
        with patch.object(OIDCConfig.objects, "order_by") as order_by:
            order_by.return_value.first.return_value = None  # simulate losing the creation race
            second = OIDCConfig.get_or_create_default()
        self.assertEqual(first.pk, second.pk)
