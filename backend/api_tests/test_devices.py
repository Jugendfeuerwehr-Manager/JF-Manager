from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from users.models import UserSession

User = get_user_model()
PASSWORD = "Synthetic-Passw0rd!"


def browser(username, agent):
    client = APIClient(enforce_csrf_checks=True, HTTP_USER_AGENT=agent)
    client.get("/api/v1/auth/session/")
    client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
    response = client.post("/api/v1/auth/session/login/", {"username": username, "password": PASSWORD}, format="json")
    assert response.data["authenticated"], response.data
    client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
    return client


class DeviceTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="device-user", password=PASSWORD)
        self.laptop = browser("device-user", "Synthetic Laptop Browser " + "x" * 300)
        self.phone = browser("device-user", "Synthetic Phone Browser")

    def devices(self, client):
        response = client.get("/api/v1/auth/devices/")
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_lists_own_devices_with_current_marker_and_short_agent(self):
        devices = self.devices(self.laptop)
        self.assertEqual(len(devices), 2)
        current = [device for device in devices if device["current"]]
        self.assertEqual(len(current), 1)
        self.assertTrue(current[0]["user_agent"].startswith("Synthetic Laptop"))
        self.assertEqual(len(current[0]["user_agent"]), 200)
        self.assertNotIn("ip", current[0])

    def test_revoking_another_device_ends_its_session(self):
        phone = next(device for device in self.devices(self.laptop) if not device["current"])
        response = self.laptop.post(f"/api/v1/auth/devices/{phone['id']}/revoke/")
        self.assertEqual(response.data, {"revoked": 1, "current": False})
        self.assertEqual(self.phone.get("/api/v1/users/me/").status_code, 401)
        self.assertEqual(self.laptop.get("/api/v1/users/me/").status_code, 200)

    def test_revoke_others_keeps_only_this_device(self):
        browser("device-user", "Synthetic Tablet")
        response = self.laptop.post("/api/v1/auth/devices/revoke-others/")
        self.assertEqual(response.data["revoked"], 2)
        self.assertEqual(len(self.devices(self.laptop)), 1)
        self.assertEqual(self.phone.get("/api/v1/users/me/").status_code, 401)

    def test_revoking_the_current_device_signs_out(self):
        current = next(device for device in self.devices(self.laptop) if device["current"])
        self.assertTrue(self.laptop.post(f"/api/v1/auth/devices/{current['id']}/revoke/").data["current"])
        self.assertEqual(self.laptop.get("/api/v1/users/me/").status_code, 401)

    def test_foreign_devices_are_not_visible_or_revocable(self):
        User.objects.create_user(username="other-user", password=PASSWORD)
        other = browser("other-user", "Synthetic Other")
        foreign = self.devices(other)[0]
        self.assertEqual(len(self.devices(self.laptop)), 2)
        self.assertEqual(self.laptop.post(f"/api/v1/auth/devices/{foreign['id']}/revoke/").status_code, 404)
        self.assertEqual(other.get("/api/v1/users/me/").status_code, 200)

    def test_logout_removes_the_device_and_revoke_requires_csrf(self):
        self.phone.post("/api/v1/auth/session/logout/")
        self.assertEqual(UserSession.objects.count(), 1)
        self.laptop.credentials()
        self.assertEqual(self.laptop.post("/api/v1/auth/devices/revoke-others/").status_code, 403)
