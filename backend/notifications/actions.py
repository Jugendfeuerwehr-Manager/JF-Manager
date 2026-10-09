"""Quick-action links from notifications (NOTIF-01.4, concept 4.9.4, decision E12).

A link carries a signed token with ids only. Opening it never changes anything: the
frontend signs the person in, calls ``resolve`` and, after a confirmation where the action
has effects, ``execute``. Both re-check the addressed account, the object and the *current*
rights. Actions are target states and therefore idempotent: if the state is already reached
or was changed by somebody else the current state is returned instead of an error.
"""

from __future__ import annotations

import logging
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.utils import timezone

security_log = logging.getLogger("security.notifications")

SALT = "jf.notify.action.v1"
DEFAULT_VALIDITY = timedelta(days=14)
MAX_TOKEN_LENGTH = 2000

READY, DONE, NOT_AVAILABLE = "ready", "done", "not_available"
DIRECT, CONFIRM = "direct", "confirm"


class InvalidToken(Exception):
    """Signature or structure is wrong."""


class WrongAccount(Exception):
    """The link was addressed to another account."""


class Expired(Exception):
    pass


class Gone(Exception):
    """Object deleted or rights withdrawn; deliberately not distinguished (4.9.4)."""


# ---------------------------------------------------------------- routes and texts


def generic_route(user):
    """Target that reveals nothing about the object."""
    return "/portal" if getattr(user, "account_kind", "") == "portal" else "/"


def safe_route(value, fallback="/"):
    """Same-origin relative path with a single leading slash, else ``fallback``."""
    if not isinstance(value, str) or len(value) > 300:
        return fallback
    if not value.startswith("/") or value.startswith("//") or "\\" in value or re.search(r"[\x00-\x1f]", value):
        return fallback
    return value


WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _when(session):
    return f"{WEEKDAYS[session.date.weekday()]} {session.date:%d.%m.%Y} · {session.start_time:%H:%M}"


# ---------------------------------------------------------------- tokens


@dataclass(frozen=True)
class Action:
    key: str
    mode: str
    check: Callable  # (user, objects) -> context; raises Gone / NotImplementedError
    preview: Callable  # (user, objects, ctx) -> dict(title, lines, state, target_route, payload_fields?)
    execute: Callable  # (user, objects, ctx, payload) -> dict(state, message, lines?, target_route, undo?)
    expiry_cap: Callable | None = None  # (objects) -> datetime | None, e.g. session start


REGISTRY: dict[str, Action] = {}


def register(action):
    REGISTRY[action.key] = action
    return action


def make_link(user, action, objects, expires_at=None):
    """Absolute URL ``{FRONTEND_URL}/a/<token>`` for ``action`` on ``objects`` addressed to ``user``."""
    entry = REGISTRY.get(action)
    if entry is None:
        raise ValueError(f"Unknown action: {action}")
    now = timezone.now()
    expires_at = expires_at or now + DEFAULT_VALIDITY
    cap = entry.expiry_cap(objects) if entry.expiry_cap else None
    if cap is not None:
        expires_at = min(expires_at, cap)
    token = signing.dumps(
        {
            "u": getattr(user, "pk", user),
            "k": action,
            "o": objects,
            "n": secrets.token_urlsafe(6),
            "e": int(expires_at.timestamp()),
        },
        salt=SALT,
        compress=True,
    )
    return f"{settings.FRONTEND_URL.rstrip('/')}/a/{token}"


def read_token(token):
    if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
        raise InvalidToken()
    try:
        data = signing.loads(token, salt=SALT)
    except signing.BadSignature as error:
        raise InvalidToken() from error
    if not (
        isinstance(data, dict)
        and isinstance(data.get("u"), int)
        and isinstance(data.get("k"), str)
        and isinstance(data.get("o"), dict)
        and isinstance(data.get("e"), int | float)
    ):
        raise InvalidToken()
    return data


def _open(user, token):
    """Validated token data and its registry entry, checking account and expiry."""
    data = read_token(token)
    if data["u"] != user.pk:
        raise WrongAccount()
    if timezone.now().timestamp() > data["e"]:
        raise Expired()
    action = REGISTRY.get(data["k"])
    if action is None:
        raise InvalidToken()
    return data, action


def _unavailable(user, title="Diese Aktion ist nicht verfügbar", lines=()):
    return {
        "mode": CONFIRM,
        "state": NOT_AVAILABLE,
        "title": title,
        "lines": list(lines),
        "target_route": generic_route(user),
    }


def resolve(user, token):
    data, action = _open(user, token)
    try:
        ctx = action.check(user, data["o"])
    except NotImplementedError:
        return {"action": action.key, **_unavailable(user)}
    body = action.preview(user, data["o"], ctx)
    return {"action": action.key, "mode": action.mode, **body}


def execute(user, token, payload=None):
    data, action = _open(user, token)
    try:
        ctx = action.check(user, data["o"])
    except NotImplementedError:
        return {"action": action.key, **_unavailable(user)}
    result = action.execute(user, data["o"], ctx, payload if isinstance(payload, dict) else {})
    security_log.info(
        "quick action executed action=%s user=%s objects=%s state=%s",
        action.key,
        user.pk,
        data["o"],
        result.get("state"),
    )
    return {"action": action.key, "mode": action.mode, **result}


# ---------------------------------------------------------------- open / inbox / preferences


def _route_check(user, objects):
    return safe_route(objects.get("r"), generic_route(user))


register(
    Action(
        "open",
        DIRECT,
        _route_check,
        lambda user, o, route: {"title": "Ansicht öffnen", "lines": [], "state": READY, "target_route": route},
        lambda user, o, route, p: {"state": DONE, "message": "", "target_route": route},
    )
)


def _inbox_entry(user, objects):
    from .inbox import may_see
    from .models import InboxRecipient

    item_id = objects.get("i")
    entry = (
        InboxRecipient.objects.select_related("item", "item__done_by", "item__department")
        .filter(user=user, item_id=item_id if isinstance(item_id, int) else None, hidden_at__isnull=True)
        .first()
    )
    if entry is None or not may_see(user, entry.item):
        raise Gone()
    return entry


def _inbox_route(user, entry):
    return safe_route(entry.item.link, "/eingang" if generic_route(user) == "/" else "/portal")


def _read_preview(user, objects, entry):
    return {
        "title": "Hinweis als gelesen markieren",
        "lines": [entry.item.title],
        "state": DONE if entry.read_at else READY,
        "target_route": _inbox_route(user, entry),
    }


def _read_execute(user, objects, entry, payload):
    if entry.read_at is None:
        entry.read_at = timezone.now()
        entry.save(update_fields=["read_at"])
    return {"state": DONE, "message": "Als gelesen markiert.", "target_route": _inbox_route(user, entry)}


register(Action("inbox_read", DIRECT, _inbox_entry, _read_preview, _read_execute))


def _task_entry(user, objects):
    from portal.access import is_portal_account

    from .models import InboxItem

    if is_portal_account(user):
        raise Gone()
    entry = _inbox_entry(user, objects)
    if entry.item.item_type != InboxItem.ItemType.TASK:
        raise Gone()
    return entry


def _task_state(item):
    if item.task_state != "done":
        return READY, []
    who = item.done_by.get_full_name() or item.done_by.username if item.done_by_id else None
    when = f" am {timezone.localtime(item.done_at):%d.%m.%Y}" if item.done_at else ""
    return DONE, [f"Bereits erledigt{f' von {who}' if who else ''}{when}."]


def _task_preview(user, objects, entry):
    state, extra = _task_state(entry.item)
    lines = [entry.item.title, *([entry.item.department.name] if entry.item.department_id else []), *extra]
    return {
        "title": "Aufgabe als erledigt markieren?",
        "lines": lines,
        "state": state,
        "target_route": _inbox_route(user, entry),
    }


def _task_execute(user, objects, entry, payload):
    from .models import InboxItem

    changed = InboxItem.objects.filter(pk=entry.item_id, task_state=InboxItem.TaskState.OPEN).update(
        task_state=InboxItem.TaskState.DONE, done_by=user, done_at=timezone.now(), done_via="email_action"
    )
    item = InboxItem.objects.select_related("done_by", "department").get(pk=entry.item_id)
    _, extra = _task_state(item)
    return {
        "state": DONE,
        "message": "Aufgabe erledigt." if changed else (extra[0] if extra else "Bereits erledigt."),
        "target_route": _inbox_route(user, entry),
    }


register(Action("task_done", CONFIRM, _task_entry, _task_preview, _task_execute))

KIND = re.compile(r"[a-z0-9_]{1,30}")


def _pref_kind(user, objects):
    kind = objects.get("k")
    if not isinstance(kind, str) or not KIND.fullmatch(kind):
        raise Gone()
    return kind


def _settings_route(user):
    return "/portal/profil" if generic_route(user) == "/portal" else "/profile"


def _set_email(user, kind, value):
    from .models import NotificationPreference

    NotificationPreference.objects.update_or_create(user=user, kind=kind, defaults={"email": value})


def _email_enabled(user, kind):
    from .models import NotificationPreference

    row = NotificationPreference.objects.filter(user=user, kind=kind).first()
    return row.email if row else True


def _unsubscribe_preview(user, objects, kind):
    return {
        "title": "Benachrichtigungsart abbestellen",
        "lines": ["E-Mails dieser Art werden nicht mehr gesendet. Der Eingang bleibt unverändert."],
        "state": READY if _email_enabled(user, kind) else DONE,
        "target_route": _settings_route(user),
    }


def _unsubscribe_execute(user, objects, kind, payload):
    _set_email(user, kind, False)
    undo = make_link_token(user, "subscribe", {"k": kind})
    return {
        "state": DONE,
        "message": "Abbestellt. Du kannst das in den Einstellungen rückgängig machen.",
        "target_route": _settings_route(user),
        "undo": {"label": "Rückgängig", "token": undo},
    }


def _subscribe_execute(user, objects, kind, payload):
    _set_email(user, kind, True)
    return {
        "state": DONE,
        "message": "E-Mails dieser Art sind wieder aktiviert.",
        "target_route": _settings_route(user),
    }


def _subscribe_preview(user, objects, kind):
    return {
        "title": "E-Mails dieser Art wieder aktivieren",
        "lines": [],
        "state": DONE if _email_enabled(user, kind) else READY,
        "target_route": _settings_route(user),
    }


register(Action("unsubscribe", DIRECT, _pref_kind, _unsubscribe_preview, _unsubscribe_execute))
register(Action("subscribe", DIRECT, _pref_kind, _subscribe_preview, _subscribe_execute))


def make_link_token(user, action, objects, expires_at=None):
    """Only the token part of ``make_link`` (used for undo hints)."""
    return make_link(user, action, objects, expires_at).rsplit("/a/", 1)[1]


# ---------------------------------------------------------------- participation (confirm)


def _session_start_of(objects):
    from participation.service import session_start
    from training.models import TrainingSession

    session = TrainingSession.objects.filter(pk=objects.get("s")).first() if isinstance(objects.get("s"), int) else None
    return session_start(session) if session else None


def _person(user, objects):
    """``(session, member, source)`` the account may act for, else ``Gone``."""
    from rest_framework.exceptions import NotFound

    from members.models import Member
    from participation import service
    from participation.models import Registration
    from participation.portal_views import portal_session_or_404
    from participation.staff_views import can_manage
    from portal.access import is_portal_account
    from portal.people import portal_children, portal_self
    from training.models import TrainingSession

    sid, mid = objects.get("s"), objects.get("m")
    if not (isinstance(sid, int) and isinstance(mid, int)):
        raise Gone()
    session = TrainingSession.objects.filter(pk=sid).first()
    member = Member.objects.filter(pk=mid).first()
    if session is None or member is None:
        raise Gone()
    if is_portal_account(user):
        own = portal_self(user)
        if own is not None and own.pk == mid:
            source = Registration.Source.PORTAL_MEMBER
        elif portal_children(user).filter(pk=mid).exists():
            source = Registration.Source.PORTAL_PARENT
        else:
            raise Gone()
        try:
            portal_session_or_404(sid, member)
        except NotFound as error:
            raise Gone() from error
    else:
        if not can_manage(user, session) or not service.is_target_member(session, mid):
            raise Gone()
        source = Registration.Source.STAFF
    return session, member, source


def _registration(session, member):
    from participation.models import Registration

    return Registration.objects.filter(session=session, member=member).first()


def _route_for(user, session):
    if generic_route(user) == "/portal":
        return f"/portal/termine/{session.pk}"
    return f"/training/sessions/{session.pk}/plan"


def _display_name(member):
    return f"{member.name} {member.lastname}".strip()


def _reason_fields():
    from participation.models import Registration

    return [
        {
            "name": "reason_category",
            "type": "choice",
            "optional": True,
            "label": "Grund",
            "choices": [{"value": v, "label": label} for v, label in Registration.Reason.choices],
        }
    ]


@dataclass(frozen=True)
class Participation:
    """What one participation action wants and when it is already reached."""

    title: str
    verb: str
    target: Callable  # (mode) -> target state
    reached: Callable  # (mode, registration) -> bool
    applicable: Callable  # (mode, registration) -> str | None (reason it cannot apply)
    fields: bool = False


def _state(registration):
    return registration.state if registration else None


PARTICIPATION = {
    "register": Participation(
        "Zum Dienst anmelden?",
        "angemeldet",
        lambda mode: "applied" if mode == "assignment" else "registered",
        lambda mode, r: (
            _state(r) in ("registered", "assigned", "waitlisted", "applied") or (r is None and mode == "opt_out")
        ),
        lambda mode, r: None,
    ),
    "cancel": Participation(
        "Vom Dienst abmelden?",
        "abgemeldet",
        lambda mode: "cancelled",
        lambda mode, r: _state(r) == "cancelled",
        lambda mode, r: None,
        fields=True,
    ),
    "withdraw": Participation(
        "Bewerbung zurückziehen?",
        "zurückgezogen",
        lambda mode: "withdrawn",
        lambda mode, r: _state(r) == "cancelled",
        lambda mode, r: None if mode == "assignment" else "Für diesen Dienst gibt es keine Bewerbung.",
    ),
    "waitlist_leave": Participation(
        "Von der Warteliste abmelden?",
        "von der Warteliste abgemeldet",
        lambda mode: "cancelled",
        lambda mode, r: _state(r) == "cancelled",
        lambda mode, r: None if _state(r) == "waitlisted" else "Du stehst nicht mehr auf der Warteliste.",
    ),
}


def _participation_mode(session):
    from participation import service

    return service.participation_for(session)[0].mode


def _lines(session, member, registration):
    lines = [session.title, _when(session), _display_name(member)]
    if registration is not None:
        lines.append(f"Aktueller Status: {registration.get_state_display()}")
    return lines


def _participation_check(user, objects):
    return _person(user, objects)


def _make_preview(key):
    spec = PARTICIPATION[key]

    def preview(user, objects, ctx):
        session, member, _source = ctx
        mode = _participation_mode(session)
        registration = _registration(session, member)
        lines = _lines(session, member, registration)
        body = {"title": spec.title, "lines": lines, "target_route": _route_for(user, session)}
        if spec.reached(mode, registration):
            return {**body, "state": DONE}
        blocked = spec.applicable(mode, registration)
        if blocked:
            return {**body, "lines": [*lines, blocked], "state": NOT_AVAILABLE}
        if spec.fields:
            body["payload_fields"] = _reason_fields()
        return {**body, "state": READY}

    return preview


def _make_execute(key):
    spec = PARTICIPATION[key]

    def run(user, objects, ctx, payload):
        from participation import service
        from participation.service import ParticipationError

        session, member, source = ctx
        route = _route_for(user, session)
        mode = _participation_mode(session)
        registration = _registration(session, member)
        if spec.reached(mode, registration):
            return {
                "state": DONE,
                "message": "Bereits erledigt.",
                "lines": _lines(session, member, registration),
                "target_route": route,
            }
        blocked = spec.applicable(mode, registration)
        if blocked:
            return {"state": NOT_AVAILABLE, "message": blocked, "target_route": route}
        reason = payload.get("reason_category") if spec.fields else ""
        try:
            registration, _changed, _plan = service.set_registration(
                session.pk,
                member.pk,
                spec.target(mode),
                actor=user,
                source=source,
                reason_category=reason if isinstance(reason, str) else "",
                via="email_action",
            )
        except ParticipationError as error:
            if error.status == 400:
                raise
            return {"state": NOT_AVAILABLE, "message": error.message, "target_route": route}
        return {
            "state": DONE,
            "message": f"{_display_name(member)} ist {spec.verb}.",
            "lines": _lines(session, member, registration),
            "target_route": route,
        }

    return run


for _key in PARTICIPATION:
    register(
        Action(
            _key,
            CONFIRM,
            _participation_check,
            _make_preview(_key),
            _make_execute(_key),
            expiry_cap=_session_start_of,
        )
    )


# ---------------------------------------------------------------- hooks for later packages


def _not_implemented(user, objects):
    raise NotImplementedError()


register(Action("apply_excused", CONFIRM, _not_implemented, lambda *a: {}, lambda *a: {}))  # PART-02: in-app only


# ---------------------------------------------------------------- change requests (PORTAL-03.4)


def _change_request(user, objects):
    """Reviewable request; portal accounts and requests outside the reviewer's scope are gone."""
    from portal.access import is_portal_account
    from portal.change_requests import reviewable

    pk = objects.get("c")
    if is_portal_account(user) or not isinstance(pk, int):
        raise Gone()
    change = reviewable(user).filter(pk=pk).first()
    if change is None:
        raise Gone()
    return change


def _review_route(change):
    return f"/portal-verwaltung?tab=antraege&antrag={change.pk}"


register(
    Action(
        "cr_review",
        DIRECT,
        _change_request,
        lambda user, o, change: {
            "title": "Änderungsantrag prüfen",
            "lines": [],
            "state": READY,
            "target_route": _review_route(change),
        },
        lambda user, o, change, p: {"state": DONE, "message": "", "target_route": _review_route(change)},
    )
)


def _apply_state(user, objects, change):
    """``(state, lines)``: decided, changed since the mail, conflicts and four-eyes block the shortcut."""
    from portal.change_requests import own_request, payload

    data = payload(change, with_current=True)
    lines = [data["person_name"], *(f"{f['label']}: {f['old'] or '–'} → {f['new'] or '–'}" for f in data["fields"])]
    if change.status != "open":
        return DONE, [*lines, f"Bereits entschieden: {change.get_status_display()}."]
    if own_request(change, user):
        return NOT_AVAILABLE, [*lines, "Eigene Anträge gibt eine andere Person frei."]
    if objects.get("v") != change.version:
        return NOT_AVAILABLE, [*lines, "Der Antrag wurde inzwischen geändert. Bitte in der Prüfansicht entscheiden."]
    if any(f["conflict"] for f in data["fields"]):
        return NOT_AVAILABLE, [
            *lines,
            "Einzelne Werte wurden inzwischen geändert. Bitte in der Prüfansicht entscheiden.",
        ]
    return READY, lines


def _apply_preview(user, objects, change):
    state, lines = _apply_state(user, objects, change)
    return {
        "title": "Alle Änderungen übernehmen?",
        "lines": lines,
        "state": state,
        "target_route": _review_route(change),
    }


def _apply_execute(user, objects, change, payload):
    from portal.change_requests import ChangeRequestError, decide

    state, lines = _apply_state(user, objects, change)
    if state != READY:
        return {"state": state, "message": lines[-1], "lines": lines, "target_route": _review_route(change)}
    try:
        decided = decide(change, user, {f["field"]: "apply" for f in change.fields}, version=change.version, note="")
    except ChangeRequestError as error:
        return {"state": NOT_AVAILABLE, "message": error.detail, "target_route": _review_route(change)}
    return {
        "state": DONE,
        "message": f"Änderungen übernommen ({decided.get_status_display()}).",
        "lines": lines,
        "target_route": _review_route(change),
    }


register(Action("cr_apply", CONFIRM, _change_request, _apply_preview, _apply_execute))
