"""Portal endpoints for registering, cancelling and absences (PART-01.4, concept 5.3).

Every person id from a request is checked against ``portal_self`` and ``portal_children``;
anything else answers 404. Responses carry the free places as a count, never names (D6), the
eligibility reasons of the addressed person only (gender conditions neutralised) and never the
reason note (D4).
"""

import json
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from portal.people import portal_children, portal_self
from portal.permissions import PortalAccountRequired
from training.models import TrainingSession

from . import service, slots, states
from .eligibility import neutral_audience_notice
from .models import Mode, Registration, SessionParticipation, Slot
from .service import ParticipationError
from .staff_views import RegistrationInput, error_response
from .throttles import PortalWriteThrottle

DEFAULT_WINDOW_DAYS = 90
MAX_SESSIONS = 200
VISIBLE = (TrainingSession.Status.PUBLISHED, TrainingSession.Status.CANCELLED)


class PortalView(APIView):
    portal_access = True
    permission_classes = [PortalAccountRequired]

    def person_for(self, request, member_id):
        """The addressed person, or 404 unless the account may act for them."""
        own = portal_self(request.user)
        if own is not None and own.pk == member_id:
            return own, Registration.Source.PORTAL_MEMBER
        child = portal_children(request.user).filter(pk=member_id).first()
        if child is None:
            raise NotFound("Person nicht gefunden.")
        return child, Registration.Source.PORTAL_PARENT


def portal_session_or_404(session_id, member):
    """Visible session whose target group contains the person, else 404 (no hint that it exists)."""
    session = TrainingSession.objects.filter(pk=session_id, status__in=VISIBLE).first()
    if session is None or not service.is_target_member(session, member.pk):
        raise NotFound("Dienst nicht gefunden.")
    participation, _ = service.participation_for(session)
    if not participation.portal_visible:
        raise NotFound("Dienst nicht gefunden.")
    return session


def person_display(mode, registration):
    if registration is not None:
        return registration.state
    return "expected" if mode == Mode.OPT_OUT else "no_response"


def _blocked(error):
    return {"code": error.code, "detail": error.message, "reasons": service.neutral_reasons(error.reasons)}


def _rule_key(participation):
    return json.dumps(participation.eligibility, sort_keys=True)


def _label(positions, slot_id):
    return next((slot.label for slot in positions if slot.pk == slot_id), None)


def build_items(member, sessions, *, now=None):
    """One portal entry per session for one person; a constant number of queries per session group."""
    now = now or timezone.now()
    ids = [s.pk for s in sessions]
    participations = {p.session_id: p for p in SessionParticipation.objects.filter(session_id__in=ids)}
    registrations = {r.session_id: r for r in Registration.objects.filter(member=member, session_id__in=ids)}
    seated = dict(
        Registration.objects.filter(session_id__in=ids, state__in=service.SEATED)
        .values_list("session_id")
        .annotate(n=Count("pk"))
        .values_list("session_id", "n")
    )
    positions_by = {}
    for slot in Slot.objects.filter(participation__session_id__in=ids):
        positions_by.setdefault(slot.participation_id, []).append(slot)
    held_by = {}
    for session_id, slot_id, count in (
        Registration.objects.filter(session_id__in=ids, state__in=service.SEATED)
        .values_list("session_id", "slot_id")
        .annotate(n=Count("pk"))
        .values_list("session_id", "slot_id", "n")
    ):
        held_by.setdefault(session_id, {})[slot_id] = count
    defaults, results, items = {}, {}, []
    for session in sessions:
        participation = participations.get(session.pk) or service.participation_for(session)[0]
        if not participation.portal_visible:
            continue
        registration = registrations.get(session.pk)
        dept_defaults = defaults.setdefault(session.department_id, service.effective_defaults(session.department_id))
        due = service.deadlines(session, participation, dept_defaults)
        rule = participation.eligibility
        result = None
        if rule:
            key = (_rule_key(participation), session.date)
            if key not in results:
                results[key] = service.eligibility_for(session, participation, [member.pk]).get(member.pk)
            result = results[key]
        positions = sorted(positions_by.get(participation.pk, []), key=lambda s: (s.position, s.pk))
        if participation.mode == Mode.OPT_OUT:
            positions = []
        fit = full = None
        if positions:
            fit = slots.fits(participation, positions, [member.pk], session.date).get(member.pk, slots.Fit())
            result = service.position_result(participation, positions, fit)
            held = dict(held_by.get(session.pk, {}))
            if registration and registration.state in service.SEATED:
                held[registration.slot_id] = held.get(registration.slot_id, 1) - 1
            if participation.mode == Mode.OPT_IN:
                full = slots.decide(participation, positions, fit, None, held).waitlist
        taken = seated.get(session.pk, 0)
        limited = participation.mode != Mode.OPT_OUT and participation.max_participants is not None
        register_target = states.APPLIED if participation.mode == Mode.ASSIGNMENT else states.REGISTERED
        flags = {}
        for name, target in (("register", register_target), ("cancel", states.CANCELLED)):
            try:
                plan = service.plan_change(
                    session,
                    participation,
                    registration,
                    target,
                    staff=False,
                    now=now,
                    seated=taken - (1 if registration and registration.state in service.SEATED else 0),
                    eligibility=result,
                    defaults=dept_defaults,
                    full=full if name == "register" else None,
                )
                # Without a row an opt-out person is already expected: nothing to confirm.
                expected = participation.mode == Mode.OPT_OUT and registration is None and name == "register"
                flags[name] = (not plan.noop and not expected, None)
            except ParticipationError as error:
                flags[name] = (False, _blocked(error))
        items.append(
            {
                "id": session.pk,
                "title": session.title,
                "date": session.date,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "place": session.location,
                "session_status": session.status,
                "mode": participation.mode,
                "public_note": participation.public_note,
                "state": person_display(participation.mode, registration),
                "waitlist_position": service.waitlist_position(registration),
                "reason_category": registration.reason_category if registration else "",
                "version": registration.version if registration else 0,
                "late": bool(registration and registration.late),
                # PART-03.5: neutral flag only, the reasons stay with the staff
                "conflict": bool(registration and registration.conflict),
                "deadlines": {
                    "registration_opens_at": due.opens_at,
                    "registration_closes_at": due.registration_closes_at,
                    "cancellation_closes_at": due.cancellation_closes_at,
                },
                "limited": limited,
                "free_places": max(participation.max_participants - taken, 0) if limited else None,
                # Total places for the bar "3 von 20 frei"; still no names (D6).
                "max_participants": participation.max_participants if limited else None,
                "eligibility": {
                    "ok": result is None or result.ok,
                    "reasons": service.neutral_reasons(result.reasons) if result is not None and not result.ok else [],
                    "audience_notice": neutral_audience_notice(rule) if rule else None,
                },
                # PART-04.3: positions with free places only, never names (D6)
                "positions": [
                    {
                        "id": slot.pk,
                        "label": slot.label,
                        "max": slot.max_count,
                        "free": max(slot.max_count - held_by.get(session.pk, {}).get(slot.pk, 0), 0),
                        "suits": fit.suits(slot),
                    }
                    for slot in positions
                ],
                "slot_label": _label(positions, registration.slot_id) if registration else None,
                "preferred_slot": registration.preferred_slot_id if registration and positions else None,
                "preferred_label": _label(positions, registration.preferred_slot_id) if registration else None,
                "may_register": flags["register"][0],
                "may_cancel": flags["cancel"][0],
                "register_blocked": flags["register"][1],
                "cancel_blocked": flags["cancel"][1],
            }
        )
    return items


class ListQuery(serializers.Serializer):
    person = serializers.IntegerField(min_value=1)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class SessionListView(PortalView):
    def get(self, request):
        params = request.query_params
        query = ListQuery(
            data={
                "person": params.get("person"),
                **{k: v for k, v in (("date_from", params.get("from")), ("date_to", params.get("to"))) if v},
            }
        )
        query.is_valid(raise_exception=True)
        member, _source = self.person_for(request, query.validated_data["person"])
        today = timezone.localdate()
        start = max(query.validated_data.get("date_from", today), today)
        end = query.validated_data.get("date_to", start + timedelta(days=DEFAULT_WINDOW_DAYS))
        if end < start or (end - start).days > service.MAX_ABSENCE_DAYS:
            raise serializers.ValidationError({"to": "Ungültiger Zeitraum."})
        now = timezone.now()
        sessions = list(
            service.target_sessions_for(member)
            .filter(status__in=VISIBLE, date__gte=start, date__lte=end)
            .order_by("date", "start_time", "pk")
            .distinct()[:MAX_SESSIONS]
        )
        # Published services that already started are not registrable any more and stay out of the list.
        sessions = [
            s for s in sessions if s.status == TrainingSession.Status.CANCELLED or service.session_start(s) > now
        ]
        return Response({"person": member.pk, "sessions": build_items(member, sessions, now=now)})


class SessionRegistrationView(PortalView):
    throttle_classes = [PortalWriteThrottle]

    def put(self, request, session_id, member_id):
        member, source = self.person_for(request, member_id)
        session = portal_session_or_404(session_id, member)
        data = RegistrationInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        try:
            service.set_registration(
                session.pk,
                member.pk,
                values["target"],
                actor=request.user,
                source=source,
                reason_category=values["reason_category"],
                reason_note=values["reason_note"],
                version=values["version"],
                accept_waitlist=values["accept_waitlist"],
                slot=values["slot"],
            )
        except ParticipationError as error:
            body = error.payload()
            body["reasons"] = service.neutral_reasons(error.reasons)
            if error.status == 422 and error.code == "not_target":
                raise NotFound("Dienst nicht gefunden.") from error
            return Response(body, status=error.status)
        return Response(build_items(member, [session])[0])


class AbsenceInput(serializers.Serializer):
    person = serializers.IntegerField(min_value=1)
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    reason_category = serializers.CharField(allow_blank=True, required=False, default="", max_length=12)
    reason_note = serializers.CharField(allow_blank=True, required=False, default="", max_length=200)


def absence_input(request):
    body = request.data if isinstance(request.data, dict) else {}
    data = AbsenceInput(data={**body, "date_from": body.get("from"), "date_to": body.get("to")})
    data.is_valid(raise_exception=True)
    return data.validated_data


def _absence_row(item):
    session = item["session"]
    return {
        "id": session.pk,
        "title": session.title,
        "date": session.date,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "place": session.location,
        "state": item["state"] or "none",
        "action": item["action"],
        "skip": item["skip"],
    }


class AbsencePreviewView(PortalView):
    def post(self, request):
        values = absence_input(request)
        member, source = self.person_for(request, values["person"])
        try:
            items = service.preview_absence(member, values["date_from"], values["date_to"], source=source)
        except ParticipationError as error:
            return error_response(error)
        rows = [_absence_row(i) for i in items]
        return Response(
            {
                "person": member.pk,
                "sessions": rows,
                "will_cancel": sum(r["action"] == "cancel" for r in rows),
                "skipped": sum(r["action"] == "skip" for r in rows),
            }
        )


class AbsenceView(PortalView):
    throttle_classes = [PortalWriteThrottle]

    def post(self, request):
        values = absence_input(request)
        member, source = self.person_for(request, values["person"])
        try:
            cancelled, skipped = service.execute_absence(
                member,
                values["date_from"],
                values["date_to"],
                actor=request.user,
                source=source,
                reason_category=values["reason_category"],
                reason_note=values["reason_note"],
            )
        except ParticipationError as error:
            return error_response(error)

        def brief(session):
            return {"id": session.pk, "title": session.title, "date": session.date, "start_time": session.start_time}

        return Response(
            {
                "person": member.pk,
                "cancelled": [brief(s) for s in cancelled],
                "skipped": [{**brief(s), **reason} for s, reason in skipped],
            }
        )
