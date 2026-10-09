"""NOTIF-01.4: signed quick-action links, resolve/execute, foreign accounts, expiry, idempotence."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department
from members.models import Group, Parent
from notifications import actions
from notifications.inbox import notify
from notifications.models import InboxItem, InboxRecipient, NotificationPreference
from notifications.tests_inbox import PERM, InboxTestBase
from participation.models import Registration, RegistrationEvent
from participation.tests.helpers import configure, future_day, make_member, make_session
from portal.models import AccountLink

User = get_user_model()
RESOLVE, EXECUTE = "/api/v1/actions/resolve/", "/api/v1/actions/execute/"


def token_of(url):
    return url.rsplit("/a/", 1)[1]


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def post(client, path, token, **extra):
    return client.post(path, {"token": token, **extra}, format="json")


class LinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("anna", password="x")

    def test_make_link_uses_frontend_url_and_carries_ids_only(self):
        with override_settings(FRONTEND_URL="https://jf.example/"):
            url = actions.make_link(self.user, "open", {"r": "/eingang"})
        self.assertTrue(url.startswith("https://jf.example/a/"))
        data = signing.loads(token_of(url), salt=actions.SALT)
        self.assertEqual((data["u"], data["k"], data["o"]), (self.user.pk, "open", {"r": "/eingang"}))
        self.assertEqual(set(data), {"u", "k", "o", "n", "e"})

    def test_unknown_action_is_refused_and_nonce_differs(self):
        with self.assertRaises(ValueError):
            actions.make_link(self.user, "nope", {})
        self.assertNotEqual(actions.make_link(self.user, "open", {}), actions.make_link(self.user, "open", {}))

    def test_default_validity_is_14_days(self):
        data = signing.loads(token_of(actions.make_link(self.user, "open", {})), salt=actions.SALT)
        self.assertAlmostEqual(data["e"], (timezone.now() + timedelta(days=14)).timestamp(), delta=5)

    def test_safe_route_rejects_external_targets(self):
        for value in ("//evil.example", "https://evil.example", "\\evil", "/a\\b", "x", None):
            self.assertEqual(actions.safe_route(value, "/"), "/")
        self.assertEqual(actions.safe_route("/portal/termine/3"), "/portal/termine/3")


class EndpointBase(InboxTestBase):
    def link(self, user, action, objects, **kw):
        return token_of(actions.make_link(user, action, objects, **kw))


class GenericEndpointTests(EndpointBase):
    def test_get_is_not_allowed_and_changes_nothing(self):
        item = notify(kind="x", category="requests", title="Hinweis", recipients=[self.anna])
        token = self.link(self.anna, "inbox_read", {"i": item.pk})
        client = client_for(self.anna)
        for path in (RESOLVE, EXECUTE):
            self.assertEqual(client.get(path, {"token": token}).status_code, 405)
        self.assertIsNone(InboxRecipient.objects.get(user=self.anna).read_at)

    def test_requires_a_session(self):
        self.assertIn(APIClient().post(RESOLVE, {"token": "x"}, format="json").status_code, (401, 403))

    def test_manipulated_token_is_400(self):
        token = self.link(self.anna, "open", {"r": "/eingang"})
        for bad in (token[:-2] + "xx", "müll", "", token + "a"):
            with self.subTest(bad=bad):
                response = post(client_for(self.anna), RESOLVE, bad)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid")

    def test_token_with_wrong_salt_or_shape_is_400(self):
        for value in (
            signing.dumps({"u": self.anna.pk}, salt="other"),
            signing.dumps({"u": self.anna.pk}, salt=actions.SALT),
            signing.dumps({"u": self.anna.pk, "k": "nope", "o": {}, "e": 9999999999}, salt=actions.SALT),
        ):
            self.assertEqual(post(client_for(self.anna), RESOLVE, value).status_code, 400)

    def test_foreign_account_is_403(self):
        token = self.link(self.anna, "open", {"r": "/eingang"})
        for path in (RESOLVE, EXECUTE):
            response = post(client_for(self.ben), path, token)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["code"], "wrong_account")

    def test_expired_is_410_with_generic_target(self):
        token = self.link(self.anna, "open", {"r": "/geheim"}, expires_at=timezone.now() - timedelta(seconds=5))
        response = post(client_for(self.anna), RESOLVE, token)
        self.assertEqual(response.status_code, 410)
        self.assertEqual((response.json()["code"], response.json()["target_route"]), ("expired", "/"))

    def test_open_is_direct_and_never_leaves_the_app(self):
        body = post(client_for(self.anna), RESOLVE, self.link(self.anna, "open", {"r": "/eingang"})).json()
        self.assertEqual((body["mode"], body["state"], body["target_route"]), ("direct", "ready", "/eingang"))
        bad = post(client_for(self.anna), RESOLVE, self.link(self.anna, "open", {"r": "//evil.example"})).json()
        self.assertEqual(bad["target_route"], "/")

    def test_hooks_are_not_available(self):
        token = self.link(self.anna, "apply_excused", {"id": 1})
        for path in (RESOLVE, EXECUTE):
            response = post(client_for(self.anna), path, token)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["state"], "not_available")

    def test_change_request_actions_outside_the_review_scope_are_gone(self):
        for key in ("cr_apply", "cr_review"):  # PORTAL-03.4; details in tests_change_requests
            token = self.link(self.anna, key, {"c": 999999, "v": 1})
            for path in (RESOLVE, EXECUTE):
                self.assertEqual(post(client_for(self.anna), path, token).status_code, 404)


class InboxActionTests(EndpointBase):
    def test_inbox_read_marks_read_once(self):
        item = notify(kind="x", category="requests", title="Hinweis", recipients=[self.anna], link="/members")
        token = self.link(self.anna, "inbox_read", {"i": item.pk})
        client = client_for(self.anna)
        body = post(client, RESOLVE, token).json()
        self.assertEqual((body["mode"], body["state"], body["target_route"]), ("direct", "ready", "/members"))
        self.assertIsNone(InboxRecipient.objects.get(user=self.anna).read_at)  # resolve alone changes nothing
        self.assertEqual(post(client, EXECUTE, token).json()["state"], "done")
        self.assertIsNotNone(InboxRecipient.objects.get(user=self.anna).read_at)
        self.assertEqual(post(client, RESOLVE, token).json()["state"], "done")
        self.assertEqual(post(client, EXECUTE, token).status_code, 200)

    def test_inbox_entry_of_somebody_else_or_deleted_is_404(self):
        item = notify(kind="x", category="requests", title="Hinweis", recipients=[self.anna])
        token = self.link(self.ben, "inbox_read", {"i": item.pk})
        self.assertEqual(post(client_for(self.ben), RESOLVE, token).status_code, 404)
        own = self.link(self.anna, "inbox_read", {"i": item.pk})
        item.delete()
        self.assertEqual(post(client_for(self.anna), EXECUTE, own).status_code, 404)

    def test_task_done_needs_confirmation_and_records_the_channel(self):
        task = notify(
            kind="cr_submitted",
            category="requests",
            title="Antrag prüfen",
            item_type="task",
            department=self.mitte,
            permission=PERM,
        )
        token = self.link(self.anna, "task_done", {"i": task.pk})
        client = client_for(self.anna)
        body = post(client, RESOLVE, token).json()
        self.assertEqual((body["mode"], body["state"]), ("confirm", "ready"))
        task.refresh_from_db()
        self.assertEqual(task.task_state, "open")
        self.assertEqual(post(client, EXECUTE, token).json()["state"], "done")
        task.refresh_from_db()
        self.assertEqual((task.task_state, task.done_by, task.done_via), ("done", self.anna, "email_action"))

    def test_task_already_done_by_a_colleague_shows_current_state(self):
        task = notify(
            kind="cr_submitted",
            category="requests",
            title="Antrag",
            item_type="task",
            department=self.mitte,
            permission=PERM,
        )
        token = self.link(self.anna, "task_done", {"i": task.pk})
        InboxItem.objects.filter(pk=task.pk).update(
            task_state="done", done_by=self.ben, done_at=timezone.now(), done_via="ui"
        )
        body = post(client_for(self.anna), RESOLVE, token).json()
        self.assertEqual(body["state"], "done")
        self.assertIn("Bereits erledigt von Ben", " ".join(body["lines"]))
        result = post(client_for(self.anna), EXECUTE, token)
        self.assertEqual((result.status_code, result.json()["state"]), (200, "done"))
        task.refresh_from_db()
        self.assertEqual((task.done_by, task.done_via), (self.ben, "ui"))

    def test_withdrawn_right_is_404(self):
        task = notify(
            kind="cr_submitted",
            category="requests",
            title="Antrag",
            item_type="task",
            department=self.mitte,
            permission=PERM,
        )
        token = self.link(self.anna, "task_done", {"i": task.pk})
        self.anna.department_roles.all().delete()
        for path in (RESOLVE, EXECUTE):
            self.assertEqual(post(client_for(self.anna), path, token).status_code, 404)
        task.refresh_from_db()
        self.assertEqual(task.task_state, "open")


class PreferenceActionTests(EndpointBase):
    def test_unsubscribe_is_direct_with_undo(self):
        token = self.link(self.anna, "unsubscribe", {"k": "reg_digest"})
        client = client_for(self.anna)
        self.assertEqual(post(client, RESOLVE, token).json()["state"], "ready")
        self.assertFalse(NotificationPreference.objects.exists())
        result = post(client, EXECUTE, token).json()
        self.assertFalse(NotificationPreference.objects.get(user=self.anna, kind="reg_digest").email)
        self.assertEqual(post(client, RESOLVE, token).json()["state"], "done")
        undo = result["undo"]["token"]
        self.assertEqual(post(client, EXECUTE, undo).json()["state"], "done")
        self.assertTrue(NotificationPreference.objects.get(user=self.anna, kind="reg_digest").email)

    def test_invalid_kind_is_404(self):
        token = self.link(self.anna, "unsubscribe", {"k": "../x"})
        self.assertEqual(post(client_for(self.anna), RESOLVE, token).status_code, 404)


class ParticipationBase(EndpointBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.dept = Department.objects.create(name="A", code="a")
        cls.group = Group.objects.create(name="Rot", department=cls.dept)
        cls.parent_user = User.objects.create_user("eltern", account_kind="portal")
        parent = Parent.objects.create(name="Eva", lastname="Test")
        cls.mia = make_member(
            cls.dept,
            "Mia",
            cls.group,
            birthday=timezone.localdate().replace(year=timezone.localdate().year - 12, day=1),
        )
        parent.children.add(cls.mia)
        AccountLink.objects.create(user=cls.parent_user, parent=parent, status="confirmed")
        cls.stranger = make_member(cls.dept, "Fremd", cls.group)
        cls.admin = User.objects.create_superuser("admin")
        cls.session = make_session(cls.dept, day=future_day(20), groups=[cls.group])

    def objects(self, member=None, session=None):
        return {"s": (session or self.session).pk, "m": (member or self.mia).pk}


class PortalParticipationTests(ParticipationBase):
    def test_cancel_for_own_child_records_email_action(self):
        token = self.link(self.parent_user, "cancel", self.objects())
        client = client_for(self.parent_user)
        body = post(client, RESOLVE, token).json()
        self.assertEqual((body["mode"], body["state"]), ("confirm", "ready"))
        self.assertEqual(body["payload_fields"][0]["name"], "reason_category")
        self.assertEqual(body["target_route"], f"/portal/termine/{self.session.pk}")
        self.assertFalse(Registration.objects.exists())  # resolve changes nothing
        result = post(client, EXECUTE, token, payload={"reason_category": "urlaub"})
        self.assertEqual((result.status_code, result.json()["state"]), (200, "done"), result.content)
        registration = Registration.objects.get()
        self.assertEqual((registration.state, registration.reason_category), ("cancelled", "urlaub"))
        self.assertEqual(registration.source, "portal_parent")
        self.assertEqual(RegistrationEvent.objects.get().via, "email_action")
        # idempotent: second run shows the current state
        self.assertEqual(post(client, EXECUTE, token).json()["state"], "done")
        self.assertEqual(RegistrationEvent.objects.count(), 1)
        self.assertEqual(post(client, RESOLVE, token).json()["state"], "done")

    def test_session_login_passes_the_portal_boundary(self):
        client = APIClient()
        client.force_login(self.parent_user)
        token = self.link(self.parent_user, "cancel", self.objects())
        for path in (RESOLVE, EXECUTE):
            self.assertEqual(post(client, path, token).status_code, 200)

    def test_register_again(self):
        Registration.objects.create(
            session=self.session, member=self.mia, state="cancelled", state_changed_at=timezone.now()
        )
        token = self.link(self.parent_user, "register", self.objects())
        client = client_for(self.parent_user)
        self.assertEqual(post(client, RESOLVE, token).json()["state"], "ready")
        self.assertEqual(post(client, EXECUTE, token).json()["state"], "done")
        self.assertEqual(Registration.objects.get().state, "registered")

    def test_foreign_child_is_404(self):
        token = self.link(self.parent_user, "cancel", self.objects(self.stranger))
        for path in (RESOLVE, EXECUTE):
            self.assertEqual(post(client_for(self.parent_user), path, token).status_code, 404)
        self.assertFalse(Registration.objects.exists())

    def test_deleted_session_is_404_and_cap_is_session_start(self):
        token = self.link(self.parent_user, "cancel", self.objects())
        data = signing.loads(token, salt=actions.SALT)
        self.assertLessEqual(data["e"], actions._session_start_of(self.objects()).timestamp())
        self.session.delete()
        self.assertEqual(post(client_for(self.parent_user), RESOLVE, token).status_code, 404)

    def test_link_for_a_started_session_is_expired(self):
        started = make_session(self.dept, day=timezone.localdate() - timedelta(days=1), groups=[self.group])
        token = self.link(self.parent_user, "cancel", self.objects(session=started))
        self.assertEqual(post(client_for(self.parent_user), RESOLVE, token).status_code, 410)

    def test_waitlist_leave_and_withdraw(self):
        configure(self.session, mode="opt_in", max_participants=1)
        Registration.objects.create(
            session=self.session, member=self.mia, state="waitlisted", state_changed_at=timezone.now()
        )
        client = client_for(self.parent_user)
        token = self.link(self.parent_user, "waitlist_leave", self.objects())
        self.assertEqual(post(client, EXECUTE, token).json()["state"], "done")
        self.assertEqual(Registration.objects.get().state, "cancelled")
        # not on a waitlist any more: reached state is "cancelled" -> done, nothing else changes
        # withdraw outside assignment mode is not available
        other = self.link(self.parent_user, "withdraw", self.objects())
        Registration.objects.update(state="registered")
        self.assertEqual(post(client, RESOLVE, other).json()["state"], "not_available")

    def test_withdraw_application(self):
        configure(self.session, mode="assignment")
        Registration.objects.create(
            session=self.session, member=self.mia, state="applied", state_changed_at=timezone.now()
        )
        token = self.link(self.parent_user, "withdraw", self.objects())
        self.assertEqual(post(client_for(self.parent_user), EXECUTE, token).json()["state"], "done")
        self.assertEqual(Registration.objects.get().state, "cancelled")

    def test_closed_deadline_reports_not_available_instead_of_error(self):
        configure(self.session, cancellation_closes_at=timezone.now() - timedelta(hours=1))
        token = self.link(self.parent_user, "cancel", self.objects())
        result = post(client_for(self.parent_user), EXECUTE, token)
        self.assertEqual((result.status_code, result.json().get("state")), (200, "not_available"), result.content)

    def test_member_account_acts_for_itself(self):
        user = User.objects.create_user("ole", account_kind="portal")
        ole = make_member(self.dept, "Ole", self.group)
        AccountLink.objects.create(user=user, member=ole, status="confirmed")
        token = self.link(user, "cancel", self.objects(ole))
        self.assertEqual(post(client_for(user), EXECUTE, token).json()["state"], "done")
        self.assertEqual(Registration.objects.get().source, "portal_member")


class StaffParticipationTests(ParticipationBase):
    def test_staff_with_right_may_act_without_right_gets_404(self):
        token = self.link(self.admin, "cancel", self.objects())
        response = post(client_for(self.admin), EXECUTE, token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["state"], "done")
        registration = Registration.objects.get()
        self.assertEqual(registration.source, "staff")
        self.assertEqual(RegistrationEvent.objects.get().via, "email_action")
        token = self.link(self.anna, "cancel", self.objects())
        self.assertEqual(post(client_for(self.anna), RESOLVE, token).status_code, 404)
