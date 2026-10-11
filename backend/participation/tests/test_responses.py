"""NOTIF-02.3: asking for a response and new responses for the calendar and the planner."""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, RoleTemplate, UserDepartmentRole
from members.models import Group, Parent
from notifications.models import EmailDelivery, InboxItem, InboxRecipient
from participation import service
from participation.models import SessionParticipation
from portal.models import AccountLink

from .helpers import configure, future_day, make_member, make_session

User = get_user_model()


def url(session, tail):
    return f"/api/v1/participation/sessions/{session.pk}/{tail}"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ResponseTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.dept = Department.objects.create(name="A", code="a")
        cls.other = Department.objects.create(name="B", code="b")
        planner_group = RoleTemplate.objects.get(key="training_planner").group
        cls.planner = User.objects.create_user("planer", email="planer@example.invalid")
        UserDepartmentRole.objects.create(user=cls.planner, department=cls.dept).groups.add(planner_group)
        cls.colleague = User.objects.create_user("kollege", email="kollege@example.invalid")
        UserDepartmentRole.objects.create(user=cls.colleague, department=cls.dept).groups.add(planner_group)
        cls.foreign = User.objects.create_user("planer-b")
        UserDepartmentRole.objects.create(user=cls.foreign, department=cls.other).groups.add(planner_group)
        cls.group = Group.objects.create(name="Rot", department=cls.dept)
        cls.mia = make_member(cls.dept, "Mia", cls.group)
        cls.ole = make_member(cls.dept, "Ole", cls.group)
        cls.paper = make_member(cls.dept, "Pia", cls.group)  # no portal account
        parent = Parent.objects.create(name="Eva", lastname="Test")
        parent.children.add(cls.mia, cls.ole)
        cls.parent_user = User.objects.create_user(
            "eva@example.invalid", email="eva@example.invalid", account_kind="portal"
        )
        AccountLink.objects.create(user=cls.parent_user, parent=parent, status="confirmed")

    def setUp(self):
        self.session = make_session(self.dept, day=future_day(20), groups=[self.group], created_by=self.planner)

    def client_for(self, user):
        client = APIClient()
        client.force_login(user)
        return client


class ResponseRequestTests(ResponseTestBase):
    def test_asks_people_without_response_and_counts_those_without_account(self):
        configure(self.session, mode="opt_in")
        service.set_registration(self.session.pk, self.ole.pk, "registered", actor=self.planner, source="staff")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_for(self.planner).post(url(self.session, "request-response/"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()["asked"], response.json()["without_account"]), (1, 1))
        notice = InboxItem.objects.get(kind="response_requested")
        self.assertIn("Mia", notice.title)
        self.assertTrue(InboxRecipient.objects.filter(item=notice, user=self.parent_user).exists())
        delivery = EmailDelivery.objects.get(kind="response_requested", user=self.parent_user)
        self.assertEqual(delivery.context["links"]["withdraw_label"], "Mia anmelden")
        self.assertIsNotNone(SessionParticipation.objects.get(session=self.session).response_requested_at)

    def test_a_second_request_within_an_hour_is_refused(self):
        client = self.client_for(self.planner)
        self.assertEqual(client.post(url(self.session, "request-response/")).status_code, 200)
        response = client.post(url(self.session, "request-response/"))
        self.assertEqual((response.status_code, response.json()["code"]), (429, "too_soon"))

    def test_rights_and_status(self):
        self.assertEqual(self.client_for(self.foreign).post(url(self.session, "request-response/")).status_code, 403)
        self.assertEqual(
            self.client_for(self.parent_user).post(url(self.session, "request-response/")).status_code, 403
        )
        self.assertIn(APIClient().post(url(self.session, "request-response/")).status_code, (401, 403))
        draft = make_session(self.dept, day=future_day(21), groups=[self.group], status="draft")
        response = self.client_for(self.planner).post(url(draft, "request-response/"))
        self.assertEqual((response.status_code, response.json()["code"]), (422, "not_open"))

    def test_config_reports_the_last_request(self):
        self.client_for(self.planner).post(url(self.session, "request-response/"))
        body = self.client_for(self.planner).get(url(self.session, "config/")).json()
        self.assertIsNotNone(body["response_requested_at"])


class NewResponsesTests(ResponseTestBase):
    NEWS = "/api/v1/participation/sessions/news/"

    def news(self, user, *sessions):
        ids = ",".join(str(s.pk) for s in sessions)
        response = self.client_for(user).get(self.NEWS, {"ids": ids})
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["sessions"]

    def test_counts_responses_of_others_until_seen(self):
        configure(self.session, mode="opt_in")
        service.set_registration(
            self.session.pk, self.mia.pk, "registered", actor=self.parent_user, source="portal_parent"
        )
        service.set_registration(self.session.pk, self.ole.pk, "registered", actor=self.planner, source="staff")
        self.assertEqual(self.news(self.planner, self.session), {str(self.session.pk): 1})  # own entry is not new
        self.assertEqual(self.news(self.colleague, self.session), {str(self.session.pk): 2})
        response = self.client_for(self.planner).post(url(self.session, "registrations/seen/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.news(self.planner, self.session), {})
        self.assertEqual(self.news(self.colleague, self.session), {str(self.session.pk): 2})

    def test_seen_reads_the_registration_notices_in_the_inbox(self):
        configure(self.session, mode="opt_in")
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(
                self.session.pk, self.mia.pk, "registered", actor=self.parent_user, source="portal_parent"
            )
        row = InboxRecipient.objects.get(item__kind="reg_received", user=self.planner)
        self.assertIsNone(row.read_at)
        self.client_for(self.planner).post(url(self.session, "registrations/seen/"))
        row.refresh_from_db()
        self.assertIsNotNone(row.read_at)

    def test_foreign_and_past_services_are_left_out(self):
        configure(self.session, mode="opt_in")
        service.set_registration(self.session.pk, self.mia.pk, "registered", actor=None, source="portal_parent")
        self.assertEqual(self.news(self.foreign, self.session), {})
        past = make_session(self.dept, day=timezone.localdate() - timedelta(days=3), groups=[self.group])
        self.assertEqual(self.news(self.colleague, past), {})
        self.assertEqual(self.client_for(self.foreign).post(url(self.session, "registrations/seen/")).status_code, 403)

    def test_invalid_ids_are_rejected(self):
        response = self.client_for(self.planner).get(self.NEWS, {"ids": "1,x"})
        self.assertEqual(response.status_code, 400)
