"""PORTAL-01.7 acceptance: no internal data in any response a portal account can reach (concept 6.3)."""

import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve
from django.utils import timezone

from departments.models import Department
from members.models import Event, EventType, Member, Parent
from portal.access import portal_route_allowed
from portal.models import AccountLink
from servicebook.models import Attendance, Service

from .test_boundary import _concrete_path, _routes

User = get_user_model()
MARKER = "GEHEIM-MARKER-7f3a"
FORBIDDEN_KEYS = {"notes", "events", "attachments", "attendance", "attendances", "event_set", "identityCardNumber"}


def _keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


class PortalDataLeakTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        department = Department.objects.create(name="Mitte")
        cls.child = Member.objects.create(
            name="Mia", lastname="Beispiel", notes=MARKER, identityCardNumber=MARKER, email="mia@example.invalid"
        )
        cls.child.departments.add(department)
        cls.parent = Parent.objects.create(name="Eva", lastname="Beispiel", notes=MARKER, email="eva@example.invalid")
        cls.parent.children.add(cls.child)
        event_type = EventType.objects.create(name="Ehrung", department=department)
        Event.objects.create(type=event_type, member=cls.child, datetime=timezone.localdate(), notes=MARKER)
        now = timezone.now()
        service = Service.objects.create(
            start=now - timedelta(hours=2),
            end=now,
            topic="Knoten",
            events=MARKER,
            description=MARKER,
            department=department,
        )
        Attendance.objects.create(person=cls.child, service=service, state="E")
        cls.user = User.objects.create_user("eva@example.invalid", password="x", account_kind="portal")
        AccountLink.objects.create(user=cls.user, parent=cls.parent, status=AccountLink.Status.CONFIRMED)

    def test_no_marker_or_internal_key_in_any_reachable_response(self):
        self.client.force_login(self.user)
        checked = []
        for pattern, _entry in _routes():
            path = _concrete_path(pattern)
            match = resolve(path)
            if not portal_route_allowed(match) or "logout" in path:
                continue
            for query in ("", f"?person={self.child.pk}", f"?parent={self.parent.pk}&member={self.child.pk}"):
                response = self.client.get(path + query)
                if response.status_code != 200 or "json" not in response.get("Content-Type", ""):
                    continue
                body = response.content.decode()
                checked.append(path + query)
                self.assertNotIn(MARKER, body, path + query)
                leaked = FORBIDDEN_KEYS & set(_keys(json.loads(body)))
                self.assertEqual(leaked, set(), path + query)
        self.assertIn("/api/v1/portal/me/", checked)
        self.assertIn("/api/v1/users/me/", checked)
