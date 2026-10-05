from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

STATUS_URL = "/api/v1/auth/session/"
LOGIN_URL = "/api/v1/auth/session/login/"
LOGOUT_URL = "/api/v1/auth/session/logout/"
PASSWORD = "Synthetic-Passw0rd!"


class SessionAuthTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="session-user", password=PASSWORD)
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        response = self.client.get(STATUS_URL)
        self.assertEqual(response.status_code, 200)
        return response.cookies[settings.CSRF_COOKIE_NAME].value

    def login(self, password=PASSWORD):
        token = self.csrf()
        return self.client.post(
            LOGIN_URL, {"username": "session-user", "password": password}, format="json", HTTP_X_CSRFTOKEN=token
        )

    def test_status_is_anonymous_and_sets_readable_csrf_cookie(self):
        response = self.client.get(STATUS_URL)
        self.assertEqual(response.data, {"authenticated": False})
        cookie = response.cookies[settings.CSRF_COOKIE_NAME]
        self.assertFalse(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    def test_login_without_csrf_token_is_rejected(self):
        response = self.client.post(LOGIN_URL, {"username": "session-user", "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)

    @override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_login_sets_rotated_http_only_session_cookie_without_tokens(self):
        self.client.cookies[settings.SESSION_COOKIE_NAME] = "attacker-chosen-session"
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["authenticated"])
        body = response.content.decode()
        for marker in ("access", "refresh", "token"):
            self.assertNotIn(marker, body)
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertNotEqual(cookie.value, "attacker-chosen-session")
        self.assertTrue(cookie["httponly"])
        self.assertTrue(cookie["secure"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["domain"], "")
        self.assertTrue(self.client.get(STATUS_URL).data["authenticated"])
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 200)

    def test_wrong_and_inactive_credentials_are_generic(self):
        wrong = self.login(password="wrong")
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        inactive = self.login()
        for response in (wrong, inactive):
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.data["detail"], "Benutzername oder Passwort ist falsch.")
        self.assertFalse(Session.objects.exists())

    def test_authenticated_write_requires_csrf(self):
        self.login()
        response = self.client.patch("/api/v1/users/me/", {"first_name": "Changed"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.first_name, "Changed")

    def test_logout_requires_csrf_and_deletes_server_session(self):
        self.login()
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(self.client.post(LOGOUT_URL).status_code, 403)
        self.assertEqual(Session.objects.count(), 1)
        token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        stolen_cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        response = self.client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"authenticated": False})
        self.assertFalse(Session.objects.exists())
        replay = APIClient()
        replay.cookies[settings.SESSION_COOKIE_NAME] = stolen_cookie
        self.assertIn(replay.get("/api/v1/users/me/").status_code, (401, 403))

    def test_login_attempts_per_username_are_limited(self):
        statuses = []
        for index in range(21):
            client = APIClient(enforce_csrf_checks=True, REMOTE_ADDR=f"10.0.0.{index + 1}")
            token = client.get(STATUS_URL).cookies[settings.CSRF_COOKIE_NAME].value
            statuses.append(
                client.post(
                    LOGIN_URL, {"username": "Session-User", "password": "wrong"}, format="json", HTTP_X_CSRFTOKEN=token
                ).status_code
            )
        self.assertEqual(statuses[:20], [401] * 20)
        self.assertEqual(statuses[20], 429)


@override_settings(SESSION_IDLE_TIMEOUT_SECONDS=1800, SESSION_MAX_AGE_SECONDS=43200)
class SessionLifetimeTests(APITestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user(username="lifetime-user", password=PASSWORD)
        self.client = APIClient(enforce_csrf_checks=True)
        self.now = 1_900_000_000
        patcher = patch("users.session_policy.time.time", side_effect=lambda: self.now)
        patcher.start()
        self.addCleanup(patcher.stop)
        token = self.client.get(STATUS_URL).cookies[settings.CSRF_COOKIE_NAME].value
        response = self.client.post(
            LOGIN_URL, {"username": "lifetime-user", "password": PASSWORD}, format="json", HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 200)

    def me(self):
        return self.client.get("/api/v1/users/me/").status_code

    def test_status_reports_deadlines(self):
        data = self.client.get(STATUS_URL).data
        self.assertEqual(data["idle_timeout_seconds"], 1800)
        self.assertEqual(data["idle_expires_at"], "2030-03-17T18:16:40+00:00")
        self.assertEqual(data["absolute_expires_at"], "2030-03-18T05:46:40+00:00")

    def test_idle_session_expires_and_is_deleted(self):
        self.now += 1799
        self.assertEqual(self.me(), 200)
        self.now += 1799
        self.assertEqual(self.me(), 200)
        self.now += 1800
        self.assertIn(self.me(), (401, 403))
        self.assertFalse(Session.objects.exists())

    def test_status_polling_does_not_extend_idle_time(self):
        for _ in range(3):
            self.now += 900
            self.client.get(STATUS_URL)
        self.assertIn(self.me(), (401, 403))

    def test_absolute_lifetime_ends_active_session(self):
        for _ in range(35):
            self.now += 1200
            self.assertEqual(self.me(), 200)
        self.now += 1199
        self.assertEqual(self.me(), 200)
        self.now += 1
        self.assertIn(self.me(), (401, 403))
        self.assertEqual(self.client.get(STATUS_URL).data, {"authenticated": False})


class LegacyCredentialRetirementTests(APITestCase):
    def test_migration_ends_existing_sessions_and_drops_token_tables(self):
        from importlib import import_module
        from types import SimpleNamespace

        from django.apps import apps
        from django.db import connection

        migration = import_module("users.migrations.0010_retire_legacy_tokens")
        User.objects.create_user(username="legacy-session", password=PASSWORD)
        self.client.login(username="legacy-session", password=PASSWORD)
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE authtoken_token (key varchar(40) PRIMARY KEY, user_id integer)")
            cursor.execute("INSERT INTO authtoken_token VALUES ('0123456789abcdef', 1)")
        self.assertEqual(Session.objects.count(), 1)
        migration.retire_legacy_credentials(apps, SimpleNamespace(connection=connection))
        self.assertFalse(Session.objects.exists())
        self.assertNotIn("authtoken_token", connection.introspection.table_names())
