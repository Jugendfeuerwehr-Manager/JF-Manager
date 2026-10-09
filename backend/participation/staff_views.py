"""Staff API for the participation of a planned service (PART-01.3)."""

import re

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from departments.role_assignments import scoped_permission
from members.models import Member
from portal.permissions import StaffAccountRequired
from training.api.permissions import can_manage_training_department
from training.models import TrainingSession

from . import changes, service, slots, states
from .eligibility import neutral_audience_notice
from .models import Mode, Registration, Slot, WaitlistMode
from .rules import Names, summarize, validate_rule
from .service import ParticipationError
from .views import MAX_TARGET, target_members

HTML_TAG = re.compile(r"<[^>]*>")


def error_response(error):
    return Response(error.payload(), status=error.status)


def display_state(mode, registration):
    if registration is not None:
        return registration.state
    return "expected" if mode == Mode.OPT_OUT else "no_response"


def load_session(pk):
    return get_object_or_404(TrainingSession.objects.select_related("department", "created_by"), pk=pk)


def can_manage(user, session):
    return can_manage_training_department(user, session.department_id)


def can_view(user, session):
    if can_manage(user, session):
        return True
    return session.status != TrainingSession.Status.DRAFT and scoped_permission(
        user, "training.view_trainingsession", session.department_id
    )


def can_read_notes(user, session):
    """D4: the short free text is for the responsible staff only."""
    return can_manage(user, session) or session.created_by_id == user.id


class StaffView(APIView):
    permission_classes = [StaffAccountRequired, IsAuthenticated]

    def session_for(self, request, pk, *, write):
        session = load_session(pk)
        allowed = can_manage(request.user, session) if write else can_view(request.user, session)
        if not allowed:
            raise PermissionDenied("Keine Berechtigung für diesen Dienst.")
        return session


# ---------------------------------------------------------------- configuration

MAX_SLOTS = 30


def no_markup(value):
    if HTML_TAG.search(value):
        raise serializers.ValidationError("Nur Klartext, keine HTML-Auszeichnung.")
    return value


class SlotInput(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    label = serializers.CharField(max_length=80, trim_whitespace=True, validators=[no_markup])
    min = serializers.IntegerField(min_value=0, max_value=500)
    max = serializers.IntegerField(min_value=1, max_value=500)
    rule = serializers.JSONField(required=False, allow_null=True)

    def validate_rule(self, value):
        if not value:
            return {}
        errors = validate_rule(value)
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate(self, attrs):
        if attrs["min"] > attrs["max"]:
            raise serializers.ValidationError({"min": "Mindestens darf nicht größer als die Zahl der Plätze sein."})
        return attrs


class ConfigSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=Mode.choices, required=False)
    portal_visible = serializers.BooleanField(required=False)
    public_note = serializers.CharField(max_length=1000, allow_blank=True, required=False, trim_whitespace=True)
    registration_opens_at = serializers.DateTimeField(allow_null=True, required=False)
    registration_closes_at = serializers.DateTimeField(allow_null=True, required=False)
    cancellation_closes_at = serializers.DateTimeField(allow_null=True, required=False)
    max_participants = serializers.IntegerField(min_value=1, max_value=10000, allow_null=True, required=False)
    min_participants = serializers.IntegerField(min_value=0, max_value=10000, allow_null=True, required=False)
    waitlist_mode = serializers.ChoiceField(choices=WaitlistMode.choices, required=False)
    eligibility = serializers.JSONField(required=False, allow_null=True)
    extra_places = serializers.IntegerField(min_value=0, max_value=500, allow_null=True, required=False)
    slots = SlotInput(many=True, required=False)
    revision = serializers.IntegerField(min_value=0)

    def validate_slots(self, value):
        if len(value) > MAX_SLOTS:
            raise serializers.ValidationError(f"Höchstens {MAX_SLOTS} Positionen.")
        seen = set()
        for item in value:
            key = item["label"].casefold()
            if key in seen:
                raise serializers.ValidationError(f"Die Position „{item['label']}“ ist doppelt.")
            seen.add(key)
        return value

    def validate_public_note(self, value):
        if HTML_TAG.search(value):
            raise serializers.ValidationError("Nur Klartext, keine HTML-Auszeichnung.")
        return value

    def validate_eligibility(self, value):
        if not value:
            return {}
        errors = validate_rule(value)
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate(self, attrs):
        current = self.context["participation"]
        start = service.session_start(self.context["session"])

        def pick(name):
            return attrs[name] if name in attrs else getattr(current, name)

        mode = pick("mode")
        if mode == Mode.OPT_OUT and attrs.get("slots"):
            raise serializers.ValidationError(
                {
                    "slots": "Im Modus „Abmeldung“ gibt es keine Positionen (Positionen setzen Anmeldung oder Zuteilung voraus)."
                }
            )
        with_slots = bool(attrs["slots"]) if "slots" in attrs else current.pk is not None and current.slots.exists()
        if with_slots:
            # The maximum is derived from the positions (concept 4.7); a sent value is ignored.
            attrs.pop("max_participants", None)
        if "max_participants" in attrs:
            sent_max = attrs["max_participants"]
        else:
            sent_max = None if with_slots else current.max_participants
        if mode == Mode.OPT_OUT and sent_max is not None:
            raise serializers.ValidationError(
                {
                    "max_participants": "Im Modus „Abmeldung“ gibt es keine Höchstzahl (Wartelisten setzen Anmeldung voraus)."
                }
            )
        low, high = pick("min_participants"), pick("max_participants")
        if not with_slots and low is not None and high is not None and low > high:
            raise serializers.ValidationError(
                {"min_participants": "Die Mindestzahl darf die Höchstzahl nicht überschreiten."}
            )
        opens, closes = pick("registration_opens_at"), pick("registration_closes_at")
        if opens is not None and closes is not None and opens > closes:
            raise serializers.ValidationError(
                {"registration_opens_at": "Die Anmeldung muss vor dem Anmeldeschluss beginnen."}
            )
        for name in ("registration_opens_at", "registration_closes_at", "cancellation_closes_at"):
            value = pick(name)
            if value is not None and value > start:
                raise serializers.ValidationError({name: "Fristen müssen vor dem Beginn des Dienstes liegen."})
        return attrs


CONFIG_FIELDS = (
    "mode",
    "portal_visible",
    "public_note",
    "registration_opens_at",
    "registration_closes_at",
    "cancellation_closes_at",
    "max_participants",
    "min_participants",
    "waitlist_mode",
    "eligibility",
    "extra_places",
)


def slot_payload(slot, held):
    return {
        "id": slot.pk,
        "label": slot.label,
        "min": slot.min_count,
        "max": slot.max_count,
        "rule": slot.rule or {},
        "rule_summary": summarize(slot.rule, Names.for_rule(slot.rule)) if slot.rule else None,
        "position": slot.position,
        "seated": held.get(slot.pk, 0),
    }


def seated_held(session):
    return slots.held_by_slot(Registration.objects.filter(session=session, state__in=service.SEATED).only("slot_id"))


def config_payload(session, participation):
    due = service.deadlines(session, participation)
    rule = participation.eligibility
    positions = slots.slots_for(participation)
    held = seated_held(session) if participation.pk else {}
    body = {name: getattr(participation, name) for name in CONFIG_FIELDS}
    body.update(
        slots=[slot_payload(slot, held) for slot in positions],
        capacity=slots.capacity(participation, positions),
        staffing=slots.staffing(participation, positions, held, seated=sum(held.values())),
        revision=participation.revision,
        session=session.pk,
        effective={
            "start": due.start,
            "registration_opens_at": due.opens_at,
            "registration_closes_at": due.registration_closes_at,
            "cancellation_closes_at": due.cancellation_closes_at,
        },
        defaults=service.effective_defaults(session.department_id),
        eligibility_summary=summarize(rule, Names.for_rule(rule)) if rule else None,
        audience_notice=neutral_audience_notice(rule) if rule else None,
    )
    return body


class SessionConfigView(StaffView):
    def get(self, request, session_id):
        session = self.session_for(request, session_id, write=False)
        participation, _ = service.participation_for(session)
        return Response(config_payload(session, participation))

    def put(self, request, session_id):
        self.session_for(request, session_id, write=True)
        with transaction.atomic():
            # Lock only the session row: PostgreSQL rejects FOR UPDATE on the nullable side of an outer join.
            session = (
                TrainingSession.objects.select_for_update(of=("self",)).select_related("department").get(pk=session_id)
            )
            participation, _ = service.participation_for(session)
            serializer = ConfigSerializer(
                data=request.data, context={"participation": participation, "session": session}
            )
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            revision = data.pop("revision")
            slot_items = data.pop("slots", None)
            if revision != participation.revision:
                error = ParticipationError(
                    "stale",
                    "Die Konfiguration wurde inzwischen geändert.",
                    status=409,
                    current=config_payload(session, participation),
                )
                return error_response(error)
            previous_mode = participation.mode
            if "eligibility" in data and data["eligibility"] is None:
                data["eligibility"] = {}
            for name, value in data.items():
                setattr(participation, name, value)
            if participation.mode == Mode.OPT_OUT:
                participation.max_participants = None
                participation.extra_places = None
                slot_items = []
            participation.revision += 1
            participation.save()
            if slot_items is not None:
                sync_slots(session, participation, slot_items, force=participation.mode == Mode.OPT_OUT)
            positions = slots.slots_for(participation)
            if positions:
                participation.max_participants = slots.capacity(participation, positions)
                participation.save(update_fields=["max_participants", "updated_at"])
            elif participation.extra_places is not None:
                participation.extra_places = None
                participation.save(update_fields=["extra_places", "updated_at"])
            changes.apply_mode_change(session, previous_mode, participation)
            service.promote_waitlist(session, participation)
        return Response(config_payload(session, participation))


def sync_slots(session, participation, items, *, force=False):
    """Replace the positions with ``items`` (kept by id, new ones created, missing ones removed).

    A position may not lose places that are taken: removing it or lowering its maximum below the
    number of people holding it is refused with a field error (``force`` skips this for opt-out,
    where positions do not exist, D5).
    """
    existing = {slot.pk: slot for slot in participation.slots.all()}
    held = seated_held(session)
    errors = {}
    keep = set()
    for index, item in enumerate(items):
        slot = existing.get(item.get("id")) if item.get("id") else None
        if item.get("id") and slot is None:
            errors[f"slots[{index}].id"] = "Unbekannte Position."
            continue
        if slot is not None:
            keep.add(slot.pk)
            if not force and held.get(slot.pk, 0) > item["max"]:
                errors[f"slots[{index}].max"] = (
                    f"„{slot.label}“ ist bereits mit {held[slot.pk]} Personen besetzt; erst umbesetzen oder abmelden."
                )
    for pk, slot in existing.items():
        if pk not in keep and held.get(pk, 0) and not force:
            errors["slots"] = f"„{slot.label}“ ist noch besetzt und kann nicht entfernt werden."
    if errors:
        raise serializers.ValidationError(errors)
    Slot.objects.filter(participation=participation).exclude(pk__in=keep).delete()
    for index, item in enumerate(items):
        values = {
            "label": item["label"],
            "min_count": item["min"],
            "max_count": item["max"],
            "rule": item.get("rule") or {},
            "position": index,
        }
        if item.get("id"):
            Slot.objects.filter(pk=item["id"]).update(**values)
        else:
            Slot.objects.create(participation=participation, **values)


# ---------------------------------------------------------------- registrations


def registration_payload(member, registration, mode, result, *, notes, position, in_target=True):
    body = {
        "member_id": member.pk,
        "name": member.name,
        "lastname": member.lastname,
        "group_id": member.group_id,
        "in_target": in_target,
        "state": display_state(mode, registration),
        "waitlist_position": position,
        "eligibility": {"ok": True, "reasons": []} if result is None else {"ok": result.ok, "reasons": result.reasons},
        "registration": None,
    }
    if registration is not None:
        body["registration"] = {
            "version": registration.version,
            "reason_category": registration.reason_category,
            "reason_note": registration.reason_note if notes else None,
            "source": registration.source,
            "late": registration.late,
            "conflict": registration.conflict,
            "conflict_reasons": registration.conflict_reasons,
            "state_changed_at": registration.state_changed_at,
            "slot": registration.slot_id,
            "preferred_slot": registration.preferred_slot_id,
        }
    return body


def counts_for(mode, participation, rows):
    counts = {state: 0 for state in Registration.State.values}
    counts.update(expected=0, no_response=0, conflicts=0, late=0)
    for row in rows:
        if not row["in_target"] and row["registration"] is None:
            continue
        key = row["state"]
        counts[key] += 1
        if row["registration"]:
            counts["conflicts"] += row["registration"]["conflict"]
            counts["late"] += row["registration"]["late"]
    seated = counts["registered"] + counts["assigned"]
    counts.update(
        seated=seated,
        max_participants=participation.max_participants,
        min_participants=participation.min_participants,
        free=None if participation.max_participants is None else max(participation.max_participants - seated, 0),
    )
    return counts


def build_rows(session, participation, user):
    members = target_members(session)
    members = list(members) if members is not None else []
    truncated = len(members) > MAX_TARGET
    members = members[:MAX_TARGET]
    registrations = {r.member_id: r for r in Registration.objects.filter(session=session)}
    target_ids = {m.pk for m in members}
    extra = Member.objects.filter(pk__in=[pk for pk in registrations if pk not in target_ids]).order_by(
        "lastname", "name", "pk"
    )
    results = service.eligibility_for(session, participation, [m.pk for m in members])
    waiting = sorted(
        (r for r in registrations.values() if r.state == Registration.State.WAITLISTED),
        key=lambda r: (r.state_changed_at, r.pk),
    )
    positions = {r.member_id: i for i, r in enumerate(waiting, start=1)}
    notes = can_read_notes(user, session)
    rows = []
    for member, in_target in [(m, True) for m in members] + [(m, False) for m in extra]:
        registration = registrations.get(member.pk)
        rows.append(
            registration_payload(
                member,
                registration,
                participation.mode,
                results.get(member.pk),
                notes=notes,
                position=positions.get(member.pk),
                in_target=in_target,
            )
        )
    return rows, truncated


class SessionRegistrationsView(StaffView):
    def get(self, request, session_id):
        session = self.session_for(request, session_id, write=False)
        participation, _ = service.participation_for(session)
        rows, truncated = build_rows(session, participation, request.user)
        due = service.deadlines(session, participation)
        positions = slots.slots_for(participation)
        held = seated_held(session) if participation.pk else {}
        return Response(
            {
                "session": {
                    "id": session.pk,
                    "title": session.title,
                    "date": session.date,
                    "start_time": session.start_time,
                    "status": session.status,
                },
                "mode": participation.mode,
                "revision": participation.revision,
                "deadlines": {
                    "registration_opens_at": due.opens_at,
                    "registration_closes_at": due.registration_closes_at,
                    "cancellation_closes_at": due.cancellation_closes_at,
                },
                "counts": counts_for(participation.mode, participation, rows),
                "slots": [slot_payload(slot, held) for slot in positions],
                "extra_places": participation.extra_places if positions else None,
                "staffing": slots.staffing(participation, positions, held, seated=sum(held.values())),
                "truncated": truncated,
                "members": rows,
            }
        )


class RegistrationInput(serializers.Serializer):
    target = serializers.ChoiceField(choices=states.TARGETS)
    reason_category = serializers.CharField(allow_blank=True, required=False, default="", max_length=12)
    reason_note = serializers.CharField(allow_blank=True, required=False, default="", max_length=200)
    version = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    accept_waitlist = serializers.BooleanField(required=False, default=True)


class MemberRegistrationView(StaffView):
    def put(self, request, session_id, member_id):
        session = self.session_for(request, session_id, write=True)
        member = Member.objects.filter(pk=member_id).first()
        if member is None:
            raise NotFound("Person nicht gefunden.")
        data = RegistrationInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        try:
            registration, changed, _plan = service.set_registration(
                session.pk,
                member.pk,
                values["target"],
                actor=request.user,
                source=Registration.Source.STAFF,
                reason_category=values["reason_category"],
                reason_note=values["reason_note"],
                version=values["version"],
                accept_waitlist=values["accept_waitlist"],
            )
        except ParticipationError as error:
            return error_response(error)
        participation, _ = service.participation_for(session)
        body = registration_payload(
            member,
            registration,
            participation.mode,
            None,
            notes=can_read_notes(request.user, session),
            position=service.waitlist_position(registration),
        )
        body["changed"] = changed
        return Response(body, status=status.HTTP_200_OK)
