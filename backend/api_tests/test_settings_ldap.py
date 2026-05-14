from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from settings_manager.models import LDAPConfig

User = get_user_model()


class LDAPSettingsAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username="ldap-admin",
            email="ldap-admin@example.com",
            password="admin123!",
        )
        self.regular_user = User.objects.create_user(
            username="ldap-user",
            email="ldap-user@example.com",
            password="user123!",
        )

    def test_superuser_can_read_ldap_settings_masked(self):
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get("/api/v1/settings/ldap/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("has_bind_password", response.data)
        self.assertNotIn("bind_password", response.data)

    def test_regular_user_cannot_read_ldap_settings(self):
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get("/api/v1/settings/ldap/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_update_ldap_settings(self):
        self.client.force_authenticate(user=self.admin_user)

        payload = {
            "enabled": False,
            "server_uri": "ldap://ldap.example.org",
            "ca_cert_file": "/etc/ssl/certs/internal-ca.pem",
            "ca_cert_content": "",
            "disable_cert_validation": False,
            "bind_dn": "cn=admin,dc=example,dc=org",
            "bind_password": "top-secret",
            "user_search_base_dn": "ou=users,dc=example,dc=org",
            "user_search_filter": "(uid=%(user)s)",
            "group_search_base_dn": "ou=groups,dc=example,dc=org",
            "group_search_filter": "(objectClass=groupOfNames)",
            "group_type": "group_of_names",
            "mirror_groups": True,
        }

        response = self.client.patch("/api/v1/settings/ldap/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["has_bind_password"])
        config = LDAPConfig.get_or_create_default()
        self.assertEqual(config.server_uri, payload["server_uri"])
        self.assertEqual(config.ca_cert_file, payload["ca_cert_file"])
        self.assertFalse(config.disable_cert_validation)

    def test_superuser_cannot_set_ca_file_and_content_together(self):
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(
            "/api/v1/settings/ldap/",
            {
                "ca_cert_file": "/etc/ssl/certs/internal-ca.pem",
                "ca_cert_content": "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ca_cert_file", response.data)

    @patch("users.ldap_tls.os.path.isfile", return_value=True)
    @patch("ldap.initialize")
    @patch("ldap.set_option")
    def test_test_connection_endpoint_success(self, ldap_set_option, ldap_initialize, _isfile):
        self.client.force_authenticate(user=self.admin_user)

        LDAPConfig.get_or_create_default()
        config = LDAPConfig.objects.first()
        config.server_uri = "ldap://ldap.example.org"
        config.ca_cert_file = "/etc/ssl/certs/internal-ca.pem"
        config.disable_cert_validation = False
        config.user_search_base_dn = "ou=users,dc=example,dc=org"
        config.user_search_filter = "(uid=%(user)s)"
        config.enabled = True
        config.save()

        mock_conn = MagicMock()
        ldap_initialize.return_value = mock_conn

        response = self.client.post("/api/v1/settings/ldap/test-connection/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["ok"])
        self.assertTrue(ldap_set_option.called)

    # ------------------------------------------------------------------
    # Unauthenticated access tests
    # ------------------------------------------------------------------

    def test_unauthenticated_cannot_read_ldap_settings(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/settings/ldap/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_test_connection(self):
        self.client.force_authenticate(user=None)
        response = self.client.post("/api/v1/settings/ldap/test-connection/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_browse(self):
        self.client.force_authenticate(user=None)
        response = self.client.post("/api/v1/settings/ldap/browse/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_list_mappings(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/ldap-department-mappings/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Regular user (no permissions) tests
    # ------------------------------------------------------------------

    def test_regular_user_cannot_test_connection(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post("/api/v1/settings/ldap/test-connection/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_browse(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post("/api/v1/settings/ldap/browse/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_list_mappings(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/v1/ldap-department-mappings/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------
    # is_staff (non-superuser) tests — must NOT bypass LDAP permissions
    # ------------------------------------------------------------------

    def test_staff_user_cannot_read_ldap_without_permission(self):
        staff_user = User.objects.create_user(
            username="ldap-staff",
            email="ldap-staff@example.com",
            password="staff123!",
            is_staff=True,
        )
        self.client.force_authenticate(user=staff_user)
        response = self.client.get("/api/v1/settings/ldap/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_cannot_browse(self):
        staff_user = User.objects.create_user(
            username="ldap-staff-browse",
            email="ldap-staff-browse@example.com",
            password="staff123!",
            is_staff=True,
        )
        self.client.force_authenticate(user=staff_user)
        response = self.client.post("/api/v1/settings/ldap/browse/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------
    # Delegated permission user tests
    # ------------------------------------------------------------------

    def test_user_with_view_permission_can_read_ldap(self):
        perm_user = User.objects.create_user(
            username="ldap-viewer",
            email="ldap-viewer@example.com",
            password="viewer123!",
        )
        perm_user.user_permissions.add(Permission.objects.get(codename="view_ldap_settings"))
        self.client.force_authenticate(user=perm_user)
        response = self.client.get("/api/v1/settings/ldap/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("bind_password", response.data)

    def test_user_with_view_permission_cannot_test_connection(self):
        perm_user = User.objects.create_user(
            username="ldap-viewer2",
            email="ldap-viewer2@example.com",
            password="viewer123!",
        )
        perm_user.user_permissions.add(Permission.objects.get(codename="view_ldap_settings"))
        self.client.force_authenticate(user=perm_user)
        response = self.client.post("/api/v1/settings/ldap/test-connection/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------
    # Browse input validation tests
    # ------------------------------------------------------------------

    def test_browse_rejects_invalid_ldap_filter(self):
        LDAPConfig.get_or_create_default()
        config = LDAPConfig.objects.first()
        config.server_uri = "ldap://ldap.example.org"
        config.save()

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            "/api/v1/settings/ldap/browse/",
            {"filter": "*))(|(objectClass=*"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["ok"])

    def test_browse_rejects_oversized_filter(self):
        LDAPConfig.get_or_create_default()
        config = LDAPConfig.objects.first()
        config.server_uri = "ldap://ldap.example.org"
        config.save()

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            "/api/v1/settings/ldap/browse/",
            {"filter": "(objectClass=" + "A" * 520 + ")"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["ok"])
