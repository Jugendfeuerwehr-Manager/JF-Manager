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
        self.assertEqual(response.data, {"authenticated": True})
        body = response.content.decode()
        for marker in ("access", "refresh", "token"):
            self.assertNotIn(marker, body)
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertNotEqual(cookie.value, "attacker-chosen-session")
        self.assertTrue(cookie["httponly"])
        self.assertTrue(cookie["secure"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["domain"], "")
        self.assertEqual(self.client.get(STATUS_URL).data, {"authenticated": True})
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
